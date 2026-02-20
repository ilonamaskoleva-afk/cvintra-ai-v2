"""
RAG Pipeline для BE исследований
Retrieval Augmented Generation с использованием знаниевой базы
"""

import logging
import json
from typing import Dict, List, Optional, Tuple

try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.schema import Document
    except ImportError:
        Document = None

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG Pipeline для генерации рекомендаций по дизайну BE исследований
    Использует векторное хранилище и LLM для контекстной генерации
    """
    
    _instance = None  # Для singleton pattern
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern - единственный экземпляр"""
        if cls._instance is None:
            cls._instance = super(RAGPipeline, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        vector_store=None,
        llm=None,
        retrieval_mode: str = "hybrid"
    ):
        """
        Инициализация RAG Pipeline
        
        Args:
            vector_store: VectorStore объект
            llm: LLM объект для генерации
            retrieval_mode: "hybrid" или "pure_retrieval"
        """
        if self._initialized:
            return
        
        self.vector_store = vector_store
        self.llm = llm
        self.retrieval_mode = retrieval_mode
        
        logger.info(f"RAG Pipeline инициализирован (mode: {retrieval_mode})")
        self._initialized = True
    
    def retrieve_context(
        self,
        query: str,
        k: int = 5,
        score_threshold: Optional[float] = None
    ) -> str:
        """
        Получить релевантный контекст из базы знаний
        
        Args:
            query: Поисковый запрос
            k: Количество документов
            score_threshold: Минимальный порог релевантности
        
        Returns:
            str: Форматированный контекст из документов
        """
        if self.vector_store is None:
            logger.warning("Vector store не инициализирован")
            return ""
        
        logger.info(f"🔍 Retrieve: '{query}'")
        
        results = self.vector_store.search(query, k=k, score_threshold=score_threshold)
        
        if not results:
            logger.warning("❌ Контекст не найден")
            return ""
        
        # Форматируем контекст
        context_parts = []
        for i, (doc, score) in enumerate(results, 1):
            source = doc.metadata.get('source', 'Unknown')
            doc_type = doc.metadata.get('type', 'document')
            priority = doc.metadata.get('priority', 5)
            
            # Вычисляем релевантность (конвертируем расстояние в similarity)
            similarity = 1 - score
            
            context_parts.append(f"""
[Источник {i}: {doc_type.upper()} | {source}]
[Релевантность: {similarity:.1%} | Приоритет: {priority}]

{doc.page_content}
""")
        
        context = "\n".join(context_parts)
        logger.info(f"✓ Получено {len(results)} релевантных документов")
        
        return context
    
    def get_design_recommendation(
        self,
        inn: str,
        cvintra: Optional[float] = None,
        administration_mode: str = "fasted"
    ) -> Dict:
        """
        Получить рекомендацию по дизайну исследования на основе CVintra
        
        Args:
            inn: Международное заболевание наименование препарата
            cvintra: Coefficient of Variation (если известна)
            administration_mode: "fasted", "fed", или "both"
        
        Returns:
            Dict с рекомендациями по дизайну
        """
        logger.info(f"🔬 Design recommendation для {inn} (CVintra: {cvintra}%)")
        
        # Формируем запрос к знаниевой базе
        query = f"""
        Требования к дизайну исследования биоэквивалентности для препарата
        с внутрисубъектной вариабельностью CVintra {cvintra}%
        в состоянии {administration_mode}
        """
        
        # Получаем контекст
        context = self.retrieve_context(query, k=5)
        
        # Базовая рекомендация на основе CVintra
        recommendation = self._get_cvintra_based_recommendation(cvintra, administration_mode)
        
        # Augment с контекстом если есть LLM
        if self.llm and context:
            recommendation = self._augment_with_llm(recommendation, context, inn)
        
        recommendation['context_used'] = context
        return recommendation
    
    def _get_cvintra_based_recommendation(
        self,
        cvintra: Optional[float],
        administration_mode: str
    ) -> Dict:
        """
        Базовая рекомендация на основе значения CVintra
        (без LLM, использует встроенные правила)
        """
        if cvintra is None:
            cvintra = 25  # Default значение
        
        # Определяем дизайн на основе CVintra
        if cvintra <= 20:
            design = "2x2 Crossover"
            sample_size_base = 12
            rationale = f"CVintra ≤ 20%: стандартный 2x2 crossover дизайн достаточен"
            complexity = "low"
        elif cvintra <= 30:
            design = "2x2 Crossover или 2x4 Crossover"
            sample_size_base = 32
            rationale = f"CVintra 21-30%: может потребоваться увеличенный размер выборки"
            complexity = "medium"
        else:
            design = "2x2/2x4 Crossover или Parallel"
            sample_size_base = 60
            rationale = f"CVintra > 30%: высокая вариабельность, требует увеличенного размера выборки или специального обоснования"
            complexity = "high"
        
        # Корректировка для fed состояния
        if administration_mode == "both":
            sample_size_base = int(sample_size_base * 1.5)
            note = "Требуется два исследования (fasted и fed)"
        else:
            note = ""
        
        # Добавляем dropout коэффициент (15%)
        final_sample_size = int(sample_size_base * 1.15)
        
        return {
            "recommended_design": design,
            "rationale": rationale,
            "cvintra_range": f"{cvintra:.1f}%",
            "administration_mode": administration_mode,
            "sample_size_base": sample_size_base,
            "dropout_rate": 0.15,
            "final_sample_size": final_sample_size,
            "washout_min_periods": 5,
            "complexity": complexity,
            "note": note,
            "regulatory_basis": [
                "Решение № 85 ЕврАзЭС",
                "ICH-GCP Guidelines",
                "EMA Bioequivalence Guidance"
            ]
        }
    
    def _augment_with_llm(
        self,
        base_recommendation: Dict,
        context: str,
        inn: str
    ) -> Dict:
        """
        Дополнить рекомендацию через LLM с использованием контекста
        """
        if not self.llm:
            return base_recommendation
        
        logger.info("📚 Augment with LLM")
        
        prompt = f"""
На основе следующего контекста из регуляторной документации, 
уточни рекомендацию по дизайну BE исследования для препарата {inn}.

КОНТЕКСТ ИЗ БАЗ ЗНАНИЙ:
{context}

ТЕКУЩАЯ РЕКОМЕНДАЦИЯ:
{json.dumps(base_recommendation, ensure_ascii=False, indent=2)}

Уточни и расширь рекомендацию, учитывая:
1. Специфические требования регулятора
2. Примеры похожих препаратов
3. Практические рекомендации

Ответь в формате JSON с теми же ключами, но с улучшенным содержимым.
"""
        
        try:
            response = self.llm.generate(prompt)
            
            # Парсим JSON ответ
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                augmented = json.loads(json_match.group())
                augmented['context_used'] = context
                logger.info("✓ LLM augmentation successful")
                return augmented
        except Exception as e:
            logger.warning(f"LLM augmentation failed: {str(e)}, используется базовая рекомендация")
        
        return base_recommendation
    
    def get_regulatory_requirements(self, country: str = "russia") -> Dict:
        """
        Получить регуляторные требования для конкретной страны
        
        Args:
            country: "russia", "eu", или "us"
        
        Returns:
            Dict с требованиями
        """
        query = f"Требования {country} для биоэквивалентности"
        
        context = self.retrieve_context(query, k=3)
        
        return {
            "country": country,
            "context": context,
            "sources_used": "Knowledge Base"
        }
    
    def format_synopsis_context(self, study_parameters: Dict) -> str:
        """
        Форматировать контекст для синопсиса протокола
        
        Args:
            study_parameters: Параметры исследования
        
        Returns:
            str: Форматированный контекст
        """
        inn = study_parameters.get('inn', 'Unknown')
        cvintra = study_parameters.get('cvintra', 25)
        
        query = f"Пример протокола BE исследования для {inn} с CVintra {cvintra}%"
        
        context = self.retrieve_context(query, k=3)
        
        return f"""
ПРИМЕРЫ ПРОТОКОЛОВ ИЗ БАЗЫ ЗНАНИЙ:
{context}

ПАРАМЕТРЫ ТЕКУЩЕГО ИССЛЕДОВАНИЯ:
{json.dumps(study_parameters, ensure_ascii=False, indent=2)}
"""
    
    def is_ready(self) -> bool:
        """Проверка готовности RAG pipeline"""
        return (self.vector_store is not None and 
                self.vector_store.is_loaded())
