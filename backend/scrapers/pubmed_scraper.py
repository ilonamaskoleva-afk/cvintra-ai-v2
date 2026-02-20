import requests
from bs4 import BeautifulSoup
import time
import logging
import os
import json
import sqlite3
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    from Bio import Entrez
    BIO_AVAILABLE = True
except ImportError:
    BIO_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Bio.Entrez не доступен. Установите biopython для работы с PubMed API.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SourceInfo:
    """Information about a data source (article)"""
    pmid: str
    url: str
    title: str
    year: int
    method: str  # 'regex' or 'llm'
    confidence: float
    value: Optional[float] = None
    article_type: str = "other"  # 'clinical_trial', 'review', 'other'
    subject_type: str = "human"  # 'human', 'animal', 'in_vitro'


class CacheManager:
    """SQLite-based caching for PubMed data and extractions"""

    def __init__(self, db_path: str = "backend/cache/pubmed_cache.db"):
        """Initialize cache database"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Articles cache
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        pmid TEXT PRIMARY KEY,
                        title TEXT,
                        abstract TEXT,
                        authors TEXT,
                        year INTEGER,
                        url TEXT,
                        cached_at TIMESTAMP,
                        article_type TEXT
                    )
                """)
                
                # CVintra extractions cache
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cvintra_extractions (
                        hash_key TEXT PRIMARY KEY,
                        pmid TEXT,
                        cvintra REAL,
                        confidence REAL,
                        method TEXT,
                        evidence TEXT,
                        sources TEXT,
                        drug_name TEXT,
                        extracted_at TIMESTAMP
                    )
                """)
                
                # Query results cache
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS query_results (
                        drug_hash TEXT PRIMARY KEY,
                        drug_name TEXT,
                        results TEXT,
                        cached_at TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.debug("✓ Cache database initialized")
                
        except Exception as e:
            logger.error(f"Cache initialization error: {e}")

    def get_article(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached article"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM articles WHERE pmid = ?", (pmid,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        "pmid": row[0],
                        "title": row[1],
                        "abstract": row[2],
                        "authors": json.loads(row[3]) if row[3] else [],
                        "year": row[4],
                        "url": row[5],
                        "cached": True,
                    }
            return None
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
            return None

    def cache_article(
        self, pmid: str, title: str, abstract: str, authors: List[str], 
        year: int, url: str, article_type: str = "other"
    ):
        """Cache article data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO articles 
                    (pmid, title, abstract, authors, year, url, cached_at, article_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (pmid, title, abstract, json.dumps(authors), year, url, 
                      datetime.now().isoformat(), article_type))
                conn.commit()
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def get_cvintra(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached CVintra extraction"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT cvintra, confidence, method, evidence, sources FROM cvintra_extractions WHERE pmid = ?",
                    (pmid,)
                )
                row = cursor.fetchone()
                
                if row:
                    return {
                        "cvintra": row[0],
                        "confidence": row[1],
                        "method": row[2],
                        "evidence": row[3],
                        "sources": json.loads(row[4]) if row[4] else [],
                        "cached": True,
                    }
            return None
        except Exception as e:
            logger.warning(f"CVintra cache retrieval error: {e}")
            return None

    def cache_cvintra(
        self, pmid: str, cvintra: Optional[float], confidence: float, 
        method: str, evidence: str, sources: List[Dict], drug_name: str = ""
    ):
        """Cache CVintra extraction"""
        try:
            hash_key = hashlib.md5(f"{pmid}_{drug_name}".encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cvintra_extractions
                    (hash_key, pmid, cvintra, confidence, method, evidence, sources, drug_name, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (hash_key, pmid, cvintra, confidence, method, evidence, 
                      json.dumps(sources), drug_name, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            logger.warning(f"CVintra cache write error: {e}")

    def get_query_result(self, drug_name: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Retrieve cached query result if not expired"""
        try:
            drug_hash = hashlib.md5(drug_name.lower().encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT results, expires_at FROM query_results WHERE drug_hash = ?",
                    (drug_hash,)
                )
                row = cursor.fetchone()
                
                if row:
                    expires_at = datetime.fromisoformat(row[1])
                    if datetime.now() < expires_at:
                        return json.loads(row[0])
                    else:
                        # Expired, delete it
                        cursor.execute("DELETE FROM query_results WHERE drug_hash = ?", (drug_hash,))
                        conn.commit()
            return None
        except Exception as e:
            logger.warning(f"Query cache retrieval error: {e}")
            return None

    def cache_query_result(self, drug_name: str, result: Dict, ttl_hours: int = 24):
        """Cache complete query result"""
        try:
            drug_hash = hashlib.md5(drug_name.lower().encode()).hexdigest()
            expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO query_results
                    (drug_hash, drug_name, results, cached_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (drug_hash, drug_name, json.dumps(result), 
                      datetime.now().isoformat(), expires_at))
                conn.commit()
        except Exception as e:
            logger.warning(f"Query cache write error: {e}")

    def clear_old_entries(self, days: int = 30):
        """Clear cache entries older than specified days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM articles WHERE cached_at < ?", (cutoff_date,))
                cursor.execute("DELETE FROM cvintra_extractions WHERE extracted_at < ?", (cutoff_date,))
                conn.commit()
                logger.info(f"✓ Cleared cache entries older than {days} days")
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")


class ArticleDeduplicator:
    """Deduplication logic for PubMed articles"""

    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize title for comparison"""
        import re
        # Remove special characters, convert to lowercase, remove extra spaces
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        return ' '.join(normalized.split())

    @staticmethod
    def similarity_score(title1: str, title2: str) -> float:
        """Calculate similarity between two titles (0-1)"""
        norm1 = ArticleDeduplicator.normalize_title(title1)
        norm2 = ArticleDeduplicator.normalize_title(title2)
        
        # Simple word-based similarity
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def deduplicate(articles: List[Dict[str, Any]], threshold: float = 0.85) -> List[Dict[str, Any]]:
        """
        Remove duplicate articles based on title similarity.
        Keeps article with highest year (most recent).
        """
        if not articles:
            return []

        deduplicated = []
        processed_indices = set()

        for i, article1 in enumerate(articles):
            if i in processed_indices:
                continue

            group = [i]

            # Find similar articles
            for j, article2 in enumerate(articles[i + 1 :], start=i + 1):
                if j in processed_indices:
                    continue

                similarity = ArticleDeduplicator.similarity_score(
                    article1.get("title", ""), article2.get("title", "")
                )

                if similarity >= threshold:
                    group.append(j)
                    processed_indices.add(j)

            # Keep article with highest year from group
            best_idx = max(
                group, 
                key=lambda idx: (articles[idx].get("year", 0), idx)
            )

            deduplicated.append(articles[best_idx])
            processed_indices.add(best_idx)

        logger.info(f"✓ Deduplicated {len(articles)} articles → {len(deduplicated)}")
        return deduplicated


class SourceRanker:
    """Rank sources by reliability for CVintra data"""

    # Scoring weights
    ARTICLE_TYPE_SCORE = {
        "clinical_trial": 1.0,
        "review": 0.7,
        "observational": 0.8,
        "methodology": 0.6,
        "other": 0.5,
    }

    SUBJECT_TYPE_SCORE = {
        "human": 1.0,
        "animal": 0.5,
        "in_vitro": 0.3,
    }

    METHOD_SCORE = {
        "regex": 0.8,
        "llm": 0.7,
        "hybrid": 0.9,
    }

    @staticmethod
    def calculate_score(source: Dict[str, Any]) -> float:
        """Calculate overall reliability score for a source (0-1)"""
        article_type = source.get("article_type", "other")
        subject_type = source.get("subject_type", "human")
        method = source.get("method", "regex")
        confidence = source.get("confidence", 0.5)
        year = source.get("year", 2020)

        # Base scores
        article_score = SourceRanker.ARTICLE_TYPE_SCORE.get(article_type, 0.5)
        subject_score = SourceRanker.SUBJECT_TYPE_SCORE.get(subject_type, 0.5)
        method_score = SourceRanker.METHOD_SCORE.get(method, 0.5)

        # Recency bonus (recent articles are more relevant)
        current_year = datetime.now().year
        years_old = max(0, current_year - year)
        recency_score = max(0.5, 1.0 - (years_old * 0.02))  # -2% per year

        # Combine scores (weighted average)
        overall_score = (
            article_score * 0.35 +
            subject_score * 0.25 +
            method_score * 0.20 +
            confidence * 0.15 +
            recency_score * 0.05
        )

        return min(1.0, overall_score)

    @staticmethod
    def rank_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank and sort sources by reliability"""
        scored_sources = []

        for source in sources:
            source_copy = source.copy()
            source_copy["reliability_score"] = SourceRanker.calculate_score(source)
            scored_sources.append(source_copy)

        # Sort by score descending
        scored_sources.sort(key=lambda x: x["reliability_score"], reverse=True)
        return scored_sources


class PubMedScraper:

    def __init__(self, email: str = None, api_key: str = None, use_cache: bool = True, use_llm: bool = True):
        """
        Инициализация PubMed scraper
        
        Args:
            email: Email для Entrez API (требование NCBI). Если не указан, берется из конфига
            api_key: API ключ для Entrez API (увеличивает лимит запросов). Если не указан, берется из конфига
            use_cache: Использовать кеширование результатов
            use_llm: Использовать LLM для извлечения CVintra (требует бо́льше ресурсов)
        """
        if not BIO_AVAILABLE:
            logger.warning("Bio.Entrez не доступен. Установите biopython для работы с PubMed API.")
            return
        
        # Загружаем конфиг если доступен
        try:
            from config import Config
            self.email = email or Config.NCBI_EMAIL
            self.api_key = api_key or Config.NCBI_API_KEY
        except ImportError:
            # Если конфиг недоступен, используем значения по умолчанию
            self.email = email or os.getenv("NCBI_EMAIL", "your.email@example.com")
            self.api_key = api_key or os.getenv("NCBI_API_KEY", "")
        
        # Устанавливаем email и API ключ для Entrez
        Entrez.email = self.email
        if self.api_key:
            Entrez.api_key = self.api_key
            logger.info(f"✅ PubMed API ключ установлен: {self.api_key[:10]}...")
        else:
            logger.warning("⚠️ PubMed API ключ не установлен. Лимит запросов: 3 запроса/сек")
        
        self.base_url = "https://pubmed.ncbi.nlm.nih.gov"
        
        # Initialize cache manager
        self.cache = CacheManager() if use_cache else None
        self.use_cache = use_cache
        self.use_llm = use_llm
        
        # Initialize CVintra extractor
        try:
            from backend.llm import CVintraExtractor
            llm_handler = None
            if use_llm:
                try:
                    from backend.models.llm_handler import get_llm
                    llm_handler = get_llm()
                except Exception as e:
                    logger.warning(f"Could not initialize LLM: {e}")
            
            self.cvintra_extractor = CVintraExtractor(llm_handler=llm_handler, use_llm_fallback=use_llm)
            logger.info("✓ CVintra extractor initialized")
        except Exception as e:
            logger.warning(f"Could not initialize CVintra extractor: {e}")
            self.cvintra_extractor = None
        
        # Classification patterns for article type detection
        self.clinical_trial_patterns = [
            r'clinical trial', r'randomized', r'rct', r'crossover', r'double.?blind',
            r'bioequivalence', r'bioavailability', r'pma', r'anda'
        ]
        self.animal_patterns = [r'animal', r'mice', r'rats', r'dogs', r'sheep', r'primate', r'monkey']
        self.review_patterns = [r'review', r'meta.?analysis', r'systematic', r'meta']
    
    def search_drug(self, inn: str, keywords: list = None) -> list:
        """
        Поиск статей о препарате в PubMed
        
        Args:
            inn: International Nonproprietary Name препарата
            keywords: дополнительные ключевые слова (pharmacokinetics, bioequivalence, etc.)
        
        Returns:
            list: список PMID статей
        """
        if keywords is None:
            keywords = ["pharmacokinetics", "bioequivalence", "Cmax", "AUC"]
        
        query = f"{inn} AND ({' OR '.join(keywords)})"
        
        if not BIO_AVAILABLE:
            logger.warning("Bio.Entrez не доступен. Установите biopython для работы с PubMed API.")
            return []
        
        try:
            logger.info(f"Поиск в PubMed: {query}")
            
            # Используем API ключ если доступен (увеличивает лимит запросов)
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": 20,  # максимум 20 статей
                "sort": "relevance",
                "usehistory": "y"  # Используем history для более эффективных запросов
            }
            
            handle = Entrez.esearch(**search_params)
            record = Entrez.read(handle)
            handle.close()
            
            pmids = record["IdList"]
            total_found = record.get("Count", len(pmids))
            logger.info(f"Найдено {len(pmids)} статей (всего найдено: {total_found})")
            
            return pmids
            
        except Exception as e:
            logger.error(f"Ошибка поиска в PubMed: {e}")
            return []
    
    def fetch_article_details(self, pmid: str) -> dict:
        """
        Получить детали статьи по PMID
        """
        if not BIO_AVAILABLE:
            return {}
        
        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=pmid,
                rettype="abstract",
                retmode="xml"
            )
            
            record = Entrez.read(handle)
            handle.close()
            
            article = record['PubmedArticle'][0]
            medline = article['MedlineCitation']
            
            title = medline['Article']['ArticleTitle']
            abstract = ""
            
            if 'Abstract' in medline['Article']:
                abstract_texts = medline['Article']['Abstract']['AbstractText']
                abstract = ' '.join([str(text) for text in abstract_texts])
            
            authors = []
            if 'AuthorList' in medline['Article']:
                for author in medline['Article']['AuthorList']:
                    if 'LastName' in author and 'Initials' in author:
                        authors.append(f"{author['LastName']} {author['Initials']}")
            
            year = ""
            if 'PubDate' in medline['Article']['Journal']['JournalIssue']:
                pub_date = medline['Article']['Journal']['JournalIssue']['PubDate']
                year = pub_date.get('Year', '')
            
            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "year": year,
                "url": f"{self.base_url}/{pmid}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статьи {pmid}: {e}")
            return {}
    
    def _classify_article(self, title: str, abstract: str) -> Tuple[str, str]:
        """
        Classify article type and subject type.
        
        Returns:
            (article_type, subject_type)
            article_type: 'clinical_trial', 'review', 'observational', 'methodology', 'other'
            subject_type: 'human', 'animal', 'in_vitro'
        """
        text = f"{title} {abstract}".lower()
        
        # Classify article type
        article_type = "other"
        for pattern in self.clinical_trial_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                article_type = "clinical_trial"
                break
        
        if article_type == "other":
            for pattern in self.review_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    article_type = "review"
                    break
        
        # Classify subject type
        subject_type = "human"  # default
        for pattern in self.animal_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                subject_type = "animal"
                break
        
        if subject_type == "human":
            if re.search(r'in\s+vitro', text, re.IGNORECASE):
                subject_type = "in_vitro"
        
        return article_type, subject_type
    
    def _extract_year(self, year_str: str) -> int:
        """Extract year as integer"""
        try:
            return int(year_str)
        except (ValueError, TypeError):
            return datetime.now().year
    
    
    def extract_pk_parameters(self, articles: list) -> dict:
        """
        Извлечение PK параметров из абстрактов статей
        Использует regex для базового извлечения
        """
        import re
        
        pk_data = {
            "cmax": {"value": None, "unit": "ng/mL", "sources": []},
            "auc": {"value": None, "unit": "ng·h/mL", "sources": []},
            "tmax": {"value": None, "unit": "h", "sources": []},
            "t_half": {"value": None, "unit": "h", "sources": []},
            "cvintra": {"value": None, "unit": "%", "sources": []}
        }
        
        cvintra_values = []
        
        for article in articles:
            abstract = article.get("abstract", "").lower()
            title = article.get("title", "").lower()
            full_text = f"{title} {abstract}"
            
            # Извлечение CVintra (внутрисубъектная вариабельность)
            # Улучшенные паттерны для более точного извлечения
            cv_patterns = [
                r'cv\s*intra[-\s]?subject[:\s]+(\d+\.?\d*)\s*%',
                r'intra[-\s]?subject\s+cv[:\s]+(\d+\.?\d*)\s*%',
                r'cv\s*intra[:\s]+(\d+\.?\d*)\s*%',
                r'intra[-\s]?individual\s+cv[:\s]+(\d+\.?\d*)\s*%',
                r'within[-\s]?subject\s+cv[:\s]+(\d+\.?\d*)\s*%',
                r'cv\s*intra[-\s]?subject\s*[=:]\s*(\d+\.?\d*)\s*%',
                r'intra[-\s]?subject\s+coefficient\s+of\s+variation[:\s]+(\d+\.?\d*)\s*%',
                r'cv\s*intra[:\s]*(\d+\.?\d*)\s*%',
                r'cv\s*intra[-\s]?subject[:\s]*(\d+\.?\d*)',  # без % в конце
                r'intra[-\s]?subject\s+cv[:\s]*(\d+\.?\d*)',  # без % в конце
            ]
            
            for pattern in cv_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    try:
                        cv_value = float(match.group(1))
                        if 5 <= cv_value <= 100:  # Разумный диапазон
                            cvintra_values.append(cv_value)
                            pk_data["cvintra"]["sources"].append(article["url"])
                            break
                    except ValueError:
                        continue
            
            # Извлечение Cmax
            cmax_patterns = [
                r'cmax[:\s]*(\d+\.?\d*)\s*(ng/ml|mg/l|μg/ml|mcg/ml|ng·ml[-1]|mg·l[-1])',
                r'maximum\s+concentration[:\s]*(\d+\.?\d*)\s*(ng/ml|mg/l|μg/ml|mcg/ml|ng·ml[-1]|mg·l[-1])',
                r'c\s*max[:\s]*(\d+\.?\d*)\s*(ng/ml|mg/l|μg/ml|mcg/ml)',
                r'peak\s+concentration[:\s]*(\d+\.?\d*)\s*(ng/ml|mg/l|μg/ml|mcg/ml)',
            ]
            for pattern in cmax_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match and not pk_data["cmax"]["value"]:
                    try:
                        pk_data["cmax"]["value"] = float(match.group(1))
                        pk_data["cmax"]["unit"] = match.group(2)
                        pk_data["cmax"]["sources"].append(article["url"])
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Извлечение AUC
            auc_patterns = [
                r'auc[:\s]*(\d+\.?\d*)\s*(ng·h/ml|ng\s*h/ml|mg·h/l|μg·h/ml|mcg·h/ml|ng·h·ml[-1]|mg·h·l[-1])',
                r'area\s+under\s+curve[:\s]*(\d+\.?\d*)\s*(ng·h/ml|ng\s*h/ml|mg·h/l|μg·h/ml|mcg·h/ml)',
                r'auc0[-\s]?t[:\s]*(\d+\.?\d*)\s*(ng·h/ml|ng\s*h/ml|mg·h/l)',
                r'auc0[-\s]?∞[:\s]*(\d+\.?\d*)\s*(ng·h/ml|ng\s*h/ml|mg·h/l)',
                r'auc\s*\(0[-\s]?t\)[:\s]*(\d+\.?\d*)\s*(ng·h/ml|ng\s*h/ml)',
            ]
            for pattern in auc_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match and not pk_data["auc"]["value"]:
                    try:
                        pk_data["auc"]["value"] = float(match.group(1))
                        pk_data["auc"]["unit"] = match.group(2)
                        pk_data["auc"]["sources"].append(article["url"])
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Извлечение Tmax
            tmax_patterns = [
                r'tmax[:\s]*(\d+\.?\d*)\s*(h|hours|hr|hour)',
                r'time\s+to\s+cmax[:\s]*(\d+\.?\d*)\s*(h|hours|hr|hour)',
                r'time\s+to\s+maximum\s+concentration[:\s]*(\d+\.?\d*)\s*(h|hours|hr)',
                r't\s*max[:\s]*(\d+\.?\d*)\s*(h|hours|hr)',
            ]
            for pattern in tmax_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match and not pk_data["tmax"]["value"]:
                    try:
                        pk_data["tmax"]["value"] = float(match.group(1))
                        pk_data["tmax"]["sources"].append(article["url"])
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Извлечение T1/2
            t_half_patterns = [
                r't1/2[:\s]*(\d+\.?\d*)\s*(h|hours|hr|hour)',
                r't\s*1/2[:\s]*(\d+\.?\d*)\s*(h|hours|hr)',
                r'hal[fv][-\s]?life[:\s]*(\d+\.?\d*)\s*(h|hours|hr|hour)',
                r'elimination\s+half[-\s]?life[:\s]*(\d+\.?\d*)\s*(h|hours|hr)',
                r'terminal\s+half[-\s]?life[:\s]*(\d+\.?\d*)\s*(h|hours|hr)',
                r'apparent\s+half[-\s]?life[:\s]*(\d+\.?\d*)\s*(h|hours|hr)',
            ]
            for pattern in t_half_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match and not pk_data["t_half"]["value"]:
                    try:
                        pk_data["t_half"]["value"] = float(match.group(1))
                        pk_data["t_half"]["sources"].append(article["url"])
                        break
                    except (ValueError, IndexError):
                        continue
        
        # Вычисляем среднее CVintra если найдено несколько значений
        if cvintra_values:
            pk_data["cvintra"]["value"] = round(sum(cvintra_values) / len(cvintra_values), 2)
            logger.info(f"📊 Извлечено {len(cvintra_values)} значений CVintra, среднее: {pk_data['cvintra']['value']}%")
        
        return pk_data
    
    def get_drug_pk_data(self, inn: str) -> dict:
        """
        Production-ready pipeline for CVintra extraction from PubMed.
        
        Implements:
        1. Query caching (24h TTL)
        2. Article deduplication
        3. CVintra extraction (regex + LLM)
        4. Source ranking
        5. Aggregation
        """
        # Check cache first
        if self.use_cache and self.cache:
            cached_result = self.cache.get_query_result(inn)
            if cached_result:
                logger.info(f"✓ Returning cached result for {inn}")
                cached_result["_from_cache"] = True
                return cached_result
        
        if not BIO_AVAILABLE:
            logger.warning("Bio.Entrez не доступен. Установите biopython для работы с PubMed API.")
            return self._error_response(inn, "biopython not installed")
        
        try:
            # Step 1: Search for articles
            pmids = self.search_drug(inn)
            
            if not pmids:
                logger.info(f"Статьи не найдены для {inn}")
                return self._not_found_response(inn)
            
            # Step 2: Fetch Article details
            articles = []
            delay = 0.1 if self.api_key else 0.5
            
            logger.info(f"Загружаю детали {min(len(pmids), 20)} статей...")
            for i, pmid in enumerate(pmids[:20], 1):  # Top 20
                try:
                    # Check cache first
                    if self.use_cache and self.cache:
                        cached_article = self.cache.get_article(pmid)
                        if cached_article:
                            articles.append(cached_article)
                            logger.debug(f"  [{i}] Статья {pmid} из кеша")
                            continue
                    
                    article = self.fetch_article_details(pmid)
                    if article:
                        # Classify article
                        article_type, subject_type = self._classify_article(
                            article.get("title", ""), 
                            article.get("abstract", "")
                        )
                        article["article_type"] = article_type
                        article["subject_type"] = subject_type
                        
                        # Cache article
                        if self.use_cache and self.cache:
                            year = self._extract_year(article.get("year", ""))
                            self.cache.cache_article(
                                pmid, article["title"], article["abstract"],
                                article["authors"], year, article["url"], article_type
                            )
                        
                        articles.append(article)
                        logger.debug(f"  [{i}] Загружена статья {pmid}")
                
                except Exception as e:
                    logger.warning(f"  [{i}] Ошибка загрузки {pmid}: {str(e)[:50]}")
                
                if i < min(len(pmids), 20):
                    time.sleep(delay)
            
            if not articles:
                logger.warning(f"Не удалось загрузить статьи для {inn}")
                return self._not_found_response(inn)
            
            logger.info(f"✓ Загружено {len(articles)} статей")
            
            # Step 3: Deduplication
            articles = ArticleDeduplicator.deduplicate(articles, threshold=0.85)
            
            # Step 4: Extract CVintra using hybrid regex + LLM pipeline
            if self.cvintra_extractor:
                cvintra_value, confidence, sources, all_results = self.cvintra_extractor.extract_from_articles(
                    articles, use_llm=self.use_llm
                )
                
                # Cache extractions
                if self.use_cache and self.cache:
                    for result in all_results:
                        self.cache.cache_cvintra(
                            result.pmid,
                            result.cvintra,
                            result.confidence,
                            result.method,
                            result.evidence,
                            sources,
                            drug_name=inn
                        )
            else:
                logger.warning("CVintra extractor not available")
                cvintra_value = None
                confidence = 0.0
                sources = []
            
            # Step 5: Legacy PK parameter extraction (regex only)
            pk_data = self.extract_pk_parameters(articles)
            
            # Step 6: Rank sources by reliability
            if sources:
                # Add article metadata to sources
                for source in sources:
                    for article in articles:
                        if article.get("pmid") == source.get("pmid"):
                            source["article_type"] = article.get("article_type", "other")
                            source["subject_type"] = article.get("subject_type", "human")
                            source["year"] = self._extract_year(article.get("year", ""))
                            break
                
                sources = SourceRanker.rank_sources(sources)
            
            # Step 7: Build response
            result = {
                "drug": inn,
                "status": "success",
                "n_articles": len(articles),
                "articles": [
                    {
                        "pmid": article.get("pmid"),
                        "title": article.get("title"),
                        "year": article.get("year"),
                        "url": article.get("url"),
                        "article_type": article.get("article_type", "other"),
                        "subject_type": article.get("subject_type", "human"),
                    }
                    for article in articles
                ],
                "cvintra": cvintra_value,
                "cvintra_confidence": confidence,
                "sources": sources,
                "pk_parameters": pk_data,
                "timestamp": datetime.now().isoformat(),
            }
            
            # Cache result
            if self.use_cache and self.cache:
                self.cache.cache_query_result(inn, result, ttl_hours=24)
            
            logger.info(f"✅ Extraction complete for {inn}: CVintra={cvintra_value}% (confidence={confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline error for {inn}: {e}", exc_info=True)
            return self._error_response(inn, str(e))
    
    def _error_response(self, inn: str, error: str) -> dict:
        """Generate error response"""
        return {
            "drug": inn,
            "status": "error",
            "error": error,
            "articles": [],
            "cvintra": None,
            "sources": [],
            "n_articles": 0,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _not_found_response(self, inn: str) -> dict:
        """Generate not found response"""
        return {
            "drug": inn,
            "status": "not_found",
            "message": f"No articles found for: {inn}",
            "articles": [],
            "cvintra": None,
            "sources": [],
            "n_articles": 0,
            "search_url": f"https://pubmed.ncbi.nlm.nih.gov/?term={inn}+AND+(bioequivalence+OR+pharmacokinetics)",
            "timestamp": datetime.now().isoformat(),
        }
