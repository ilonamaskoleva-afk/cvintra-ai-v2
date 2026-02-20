"""
Генератор полного клинического синопсиса протокола BE исследования
Соответствует требованиям кейса iPharma
"""
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def _auto_fetch_pk_and_cvintra(inn: str) -> Dict[str, Any]:
    """
    Try to automatically fetch PK parameters and CVintra using available scrapers
    and LLM extractor. Returns a dict compatible with `pk_parameters`.
    This function is best-effort and will not raise on missing dependencies.
    """
    pk_result = {
        'cmax': {},
        'auc': {},
        'tmax': {},
        't_half': {},
        'cvintra': {'value': None, 'unit': '%'},
        'sources': []
    }

    try:
        # Import scrapers from backend package
        from scrapers.pubmed_scraper import PubMedScraper
        from scrapers.drugbank_scraper import DrugBankScraper
    except Exception as e:
        logger.warning(f"Auto-fetch: scrapers not available: {e}")
        return pk_result

    try:
        pubmed = PubMedScraper()
        pubmed_res = pubmed.get_drug_pk_data(inn)

        # Merge pk parameters if available
        pkp = pubmed_res.get('pk_parameters') or {}
        for key in ('cmax', 'auc', 'tmax', 't_half', 'cvintra'):
            if pkp.get(key):
                pk_result[key] = pkp.get(key)

        # Collect article abstracts for LLM context
        abstracts = []
        for a in pubmed_res.get('articles', [])[:10]:
            # try to fetch full cached article if available
            try:
                art = pubmed.cache.get_article(a.get('pmid')) if getattr(pubmed, 'cache', None) else None
                if art and art.get('abstract'):
                    abstracts.append(art.get('abstract'))
            except Exception:
                continue

        # Try DrugBank for supplementary info
        try:
            db = DrugBankScraper()
            db_res = db.get_drug_info(inn)
            # DrugBank may supply PK fields under various keys
            if isinstance(db_res, dict):
                for key_map in [('cmax','cmax'), ('auc','auc'), ('tmax','tmax'), ('t_half','t_half')]:
                    k_src = key_map[1]
                    k_dst = key_map[0]
                    if db_res.get(k_src):
                        pk_result[k_dst] = db_res.get(k_src)
                # append textual summaries
                if db_res.get('summary'):
                    abstracts.append(db_res.get('summary'))
        except Exception as e:
            logger.debug(f"DrugBank fetch failed: {e}")

        # If we have abstracts, try LLM-based QA extraction (best-effort)
        if abstracts:
            context = "\n\n".join(abstracts)
            try:
                from models.llm_handler import get_llm
                llm = get_llm()
                qa_prompt = (
                    f"Extract PK parameters for {inn} from the following context."
                    " Return JSON: {\"cvintra\":float|null, \"cmax\":{\"value\":float,\"unit\":str}|null,"
                    " \"auc\":{\"value\":float,\"unit\":str}|null, \"tmax\":float|null, \"t_half\":float|null }\n\nContext:\n" + context
                )
                resp = llm.generate_json(qa_prompt)
                if isinstance(resp, dict):
                    if resp.get('cvintra') is not None:
                        pk_result['cvintra'] = {'value': float(resp.get('cvintra')), 'unit': '%'}
                    if isinstance(resp.get('cmax'), dict):
                        pk_result['cmax'] = resp.get('cmax')
                    if isinstance(resp.get('auc'), dict):
                        pk_result['auc'] = resp.get('auc')
                    if resp.get('tmax') is not None:
                        pk_result['tmax'] = {'value': float(resp.get('tmax')), 'unit': 'h'}
                    if resp.get('t_half') is not None:
                        pk_result['t_half'] = {'value': float(resp.get('t_half')), 'unit': 'h'}
            except Exception as e:
                logger.debug(f"LLM QA extraction not available or failed: {e}")

        # Attach sources
        pk_result['sources'] = pubmed_res.get('articles', [])[:10]

    except Exception as e:
        logger.warning(f"Auto-fetch pipeline error: {e}")

    return pk_result



def generate_full_synopsis_data(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Генерирует полный синопсис протокола со всеми необходимыми секциями
    
    Args:
        analysis_data: Данные из /api/full-analysis
        
    Returns:
        dict: Полный синопсис со всеми секциями протокола
    """
    inn = analysis_data.get('inn', 'N/A')
    dosage_form = analysis_data.get('dosage_form', 'N/A')
    dosage = analysis_data.get('dosage', 'N/A')
    administration_mode = analysis_data.get('administration_mode', 'fasted')
    
    design_rec = analysis_data.get('design_recommendation', {})
    sample_size = analysis_data.get('sample_size', {})
    pk_params = analysis_data.get('pk_parameters', {})
    literature = analysis_data.get('literature', {})
    
    # Attempt auto-fetch if pk_parameters is empty or incomplete
    if not pk_params or not any([pk_params.get('cmax'), pk_params.get('auc'), pk_params.get('cvintra')]):
        logger.info(f"Auto-fetching PK parameters for {inn}...")
        try:
            auto_pk = _auto_fetch_pk_and_cvintra(inn)
            # Merge auto-fetched data with existing (auto takes precedence for empty fields)
            for key in ('cmax', 'auc', 'tmax', 't_half', 'cvintra'):
                if auto_pk.get(key):
                    if not pk_params.get(key):
                        pk_params[key] = auto_pk.get(key)
            # Merge sources
            if auto_pk.get('sources') and not pk_params.get('sources'):
                pk_params['sources'] = auto_pk.get('sources')
            logger.info(f"Auto-fetch complete for {inn}")
        except Exception as e:
            logger.warning(f"Auto-fetch failed (falling back to manual): {e}")
    
    cvintra = sample_size.get('cvintra', 25)
    recommended_design = design_rec.get('recommended_design', '2×2 Cross-over')
    
    # Определение количества периодов из дизайна
    if '4-way' in recommended_design or 'RSABE' in recommended_design:
        periods = 4
        washout_duration = "7-14 дней"
    elif '3-way' in recommended_design:
        periods = 3
        washout_duration = "7-10 дней"
    else:  # 2×2
        periods = 2
        washout_duration = "7 дней"
    
    # Определение режима приема
    admin_mode_ru = {
        'fasted': 'натощак',
        'fed': 'после еды',
        'both': 'натощак и после еды'
    }.get(administration_mode, 'натощак')
    
    synopsis = {
        # ========== ОСНОВНАЯ ИНФОРМАЦИЯ ==========
        "title": "СИНОПСИС ПРОТОКОЛА ИССЛЕДОВАНИЯ БИОЭКВИВАЛЕНТНОСТИ",
        "inn": inn,
        "dosage_form": dosage_form,
        "dosage": dosage,
        "administration_mode": administration_mode,
        "generated_date": datetime.now().strftime('%d.%m.%Y %H:%M'),
        
        # ========== 1. OBJECTIVE (ЦЕЛЬ ИССЛЕДОВАНИЯ) ==========
        "objective": {
            "primary": f"Оценка биоэквивалентности исследуемого препарата {inn} {dosage} ({dosage_form}) и референтного препарата при однократном пероральном приеме {admin_mode_ru} у здоровых добровольцев.",
            "secondary": [
                "Оценка безопасности и переносимости исследуемого и референтного препаратов",
                "Оценка фармакокинетических параметров обоих препаратов"
            ]
        },
        
        # ========== 2. STUDY DESIGN (ДИЗАЙН ИССЛЕДОВАНИЯ) ==========
        "study_design": {
            "design": recommended_design,
            "type": "Открытое, рандомизированное, сбалансированное, перекрестное исследование",
            "periods": periods,
            "washout_duration": washout_duration,
            "randomization": "Рандомизация последовательности приема препаратов",
            "blinding": "Открытое исследование",
            "rationale": design_rec.get('rationale', f'Дизайн выбран на основе CVintra={cvintra}%')
        },
        
        # ========== 3. POPULATION (ПОПУЛЯЦИЯ) ==========
        "population": {
            "type": "Здоровые добровольцы",
            "age_range": "18-45 лет",
            "gender": "Мужчины и женщины",
            "total_subjects": sample_size.get('final_sample_size', 24),
            "rationale": "Здоровые добровольцы являются стандартной популяцией для исследований биоэквивалентности"
        },
        
        # ========== 4. INCLUSION CRITERIA (КРИТЕРИИ ВКЛЮЧЕНИЯ) ==========
        "inclusion_criteria": [
            "Мужчины и женщины в возрасте от 18 до 45 лет включительно",
            "Индекс массы тела (ИМТ) от 18.5 до 30.0 кг/м²",
            "Отсутствие клинически значимых отклонений при медицинском осмотре",
            "Отсутствие клинически значимых отклонений в лабораторных показателях",
            "Отсутствие аллергических реакций на компоненты препарата",
            "Согласие на использование эффективных методов контрацепции",
            "Добровольное информированное согласие на участие в исследовании"
        ],
        
        # ========== 5. EXCLUSION CRITERIA (КРИТЕРИИ ИСКЛЮЧЕНИЯ) ==========
        "exclusion_criteria": [
            "Наличие острых или хронических заболеваний",
            "Прием лекарственных препаратов в течение 14 дней до начала исследования",
            "Курение или употребление алкоголя в течение 48 часов до приема препарата",
            "Положительный тест на наркотические вещества, алкоголь",
            "Беременность или кормление грудью",
            "Участие в клинических исследованиях в течение 3 месяцев до начала исследования",
            "Донорство крови в течение 30 дней до начала исследования"
        ],
        
        # ========== 6. PK SAMPLING (СХЕМА ЗАБОРА ПРОБ) ==========
        "pk_sampling": {
            "scheme": [
                "До приема препарата (0 ч)",
                "0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 6, 8, 12, 16, 24 часа после приема",
                "Дополнительные точки при необходимости (на основе T1/2)"
            ],
            "total_samples": "15-18 образцов на период",
            "sample_volume": "4-5 мл венозной крови",
            "storage": "Хранение при -20°C до анализа",
            "rationale": "Схема обеспечивает полное описание фармакокинетического профиля"
        },
        
        # ========== 7. ENDPOINTS (КРИТЕРИИ ОЦЕНКИ) ==========
        "endpoints": {
            "primary": [
                {
                    "parameter": "Cmax",
                    "description": "Максимальная концентрация в плазме",
                    "criterion": "90% ДИ отношения геометрических средних должен находиться в пределах 80.00% - 125.00%"
                },
                {
                    "parameter": "AUC0-t",
                    "description": "Площадь под кривой концентрация-время от 0 до последней измеряемой точки",
                    "criterion": "90% ДИ отношения геометрических средних должен находиться в пределах 80.00% - 125.00%"
                },
                {
                    "parameter": "AUC0-∞",
                    "description": "Площадь под кривой концентрация-время от 0 до бесконечности",
                    "criterion": "90% ДИ отношения геометрических средних должен находиться в пределах 80.00% - 125.00%"
                }
            ],
            "secondary": [
                "Tmax (время достижения Cmax)",
                "T1/2 (период полувыведения)",
                "Кеl (константа скорости элиминации)",
                "Безопасность и переносимость"
            ]
        },
        
        # ========== 8. BIOANALYSIS (БИОАНАЛИТИЧЕСКИЙ МЕТОД) ==========
        "bioanalysis": {
            "method": "Валидированный метод жидкостной хроматографии с масс-спектрометрическим детектированием (LC-MS/MS)",
            "validation": "Метод валидирован в соответствии с требованиями FDA/EMA",
            "parameters": {
                "linearity": "Диапазон линейности покрывает ожидаемые концентрации",
                "precision": "Внутрисерийная и межсерийная точность ≤15% (≤20% для LLOQ)",
                "accuracy": "Точность в пределах ±15% (±20% для LLOQ)",
                "lloq": "Нижний предел количественного определения определяется в ходе валидации"
            },
            "quality_control": "Контрольные образцы (QC) анализируются в каждой серии"
        },
        
        # ========== 9. SAFETY (БЕЗОПАСНОСТЬ) ==========
        "safety": {
            "monitoring": [
                "Нежелательные явления (НЯ) регистрируются на протяжении всего исследования",
                "Лабораторные показатели оцениваются до и после каждого периода",
                "ЭКГ выполняется до и после каждого периода",
                "Витальные показатели (АД, ЧСС, температура) измеряются в ключевые моменты"
            ],
            "reporting": "Все НЯ документируются и классифицируются по степени тяжести и связи с препаратом",
            "stopping_rules": "Исследование может быть прекращено при выявлении серьезных нежелательных явлений"
        },
        
        # ========== 10. STATISTICAL METHODS (СТАТИСТИЧЕСКАЯ МЕТОДОЛОГИЯ) ==========
        "statistical_methods": {
            "analysis_population": "Population: все субъекты, получившие оба препарата",
            "method": "Двусторонний 90% доверительный интервал для отношения геометрических средних (Test/Reference)",
            "transformation": "Логарифмическое преобразование для Cmax, AUC0-t, AUC0-∞",
            "model": "ANOVA с фиксированными эффектами: последовательность, период, лечение",
            "power": f"Мощность исследования ≥80% при CVintra={cvintra}%",
            "significance": "Биоэквивалентность считается доказанной, если 90% ДИ полностью находится в пределах 80.00% - 125.00%"
        },
        
        # ========== 11. PK PARAMETERS (ФАРМАКОКИНЕТИЧЕСКИЕ ПАРАМЕТРЫ) ==========
        "pk_parameters": {
            "cmax": pk_params.get('cmax', {}),
            "auc": pk_params.get('auc', {}),
            "tmax": pk_params.get('tmax', {}),
            "t_half": pk_params.get('t_half', {}),
            "cvintra": pk_params.get('cvintra', {"value": cvintra, "unit": "%"}),
            "note": "Параметры основаны на данных литературы и могут быть уточнены в ходе исследования"
        },
        
        # ========== 12. REGULATORY COMPLIANCE (РЕГУЛЯТОРНОЕ СООТВЕТСТВИЕ) ==========
        "regulatory_compliance": analysis_data.get('regulatory_check', {}),
        
        # ========== 13. LITERATURE (ЛИТЕРАТУРА) ==========
        "literature": literature,
        
        # ========== 14. SAMPLE SIZE (РАЗМЕР ВЫБОРКИ) ==========
        "sample_size": sample_size,
        
        # ========== 15. ADDITIONAL INFO (ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ) ==========
        "additional_info": {
            "study_duration": f"Общая продолжительность исследования: {periods * 2 + 7} дней (включая скрининг и финальный визит)",
            "site": "Одноцентровое исследование",
            "ethics": "Исследование проводится в соответствии с Хельсинкской декларацией и требованиями GCP",
            "approval": "Протокол подлежит одобрению этическим комитетом"
        }
    }
    
    return synopsis
