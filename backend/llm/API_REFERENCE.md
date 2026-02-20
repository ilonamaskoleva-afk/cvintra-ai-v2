# CVintra Extraction Pipeline - Developer API Documentation

## Module Structure

```
backend/
├── llm/
│   ├── cvintra_extractor.py          # Main extraction module
│   ├── __init__.py                   # Public API exports
│   └── CVINTRA_PIPELINE_README.md    # Full documentation
│
└── scrapers/
    └── pubmed_scraper.py             # Enhanced scraper with integration
```

---

## Core Classes

### CVintraResult (Dataclass)

```python
from backend.llm.cvintra_extractor import CVintraResult

@dataclass
class CVintraResult:
    cvintra: Optional[float] = None         # Extracted value (%)
    confidence: float = 0.0                 # 0-1 score
    method: str = "unknown"                 # "regex" | "llm"
    evidence: str = ""                      # Quote from text
    pmid: str = ""                          # PubMed ID
    source_url: str = ""                    # Article URL
    extracted_at: str = ""                  # ISO timestamp
    
    def is_valid(self) -> bool:
        """Check if result is valid (5-100% range)"""
        return (self.cvintra is not None and 
                5 <= self.cvintra <= 100 and 
                self.confidence > 0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with timestamp"""
```

### CVintraRegexExtractor

```python
from backend.llm.cvintra_extractor import CVintraRegexExtractor

class CVintraRegexExtractor:
    
    CV_PATTERNS: List[Tuple[str, float]]  # 15+ patterns with confidence
    
    @staticmethod
    def extract_cvintra(
        text: str,
        pmid: str = "",
        url: str = ""
    ) -> List[CVintraResult]:
        """
        Extract CVintra from text using regex patterns.
        
        Args:
            text: Abstract or full text to search
            pmid: PubMed ID for tracking
            url: Source URL for tracking
            
        Returns:
            List of CVintraResult sorted by confidence (descending)
            
        Example:
            >>> extractor = CVintraRegexExtractor()
            >>> results = extractor.extract_cvintra(
            ...     "The intra-subject CV was 25.5%",
            ...     pmid="12345678"
            ... )
            >>> if results:
            ...     print(f"Found: {results[0].cvintra}%")
        """
```

### CVintraLLMExtractor

```python
from backend.llm.cvintra_extractor import CVintraLLMExtractor

class CVintraLLMExtractor:
    
    SYSTEM_PROMPT: str  # Pharmacokinetics expert prompt
    
    def __init__(self, llm_handler=None):
        """
        Initialize LLM extractor.
        
        Args:
            llm_handler: Optional LLM handler instance
                        If None, attempts to import from models.llm_handler
        """
    
    def extract_cvintra(
        self,
        text: str,
        pmid: str = "",
        url: str = "",
        abstract_only: bool = True
    ) -> Optional[CVintraResult]:
        """
        Extract CVintra using LLM (advanced NLP).
        
        Args:
            text: Abstract or text to analyze
            pmid: PubMed ID
            url: Source URL
            abstract_only: If True, limit to 2000 chars
            
        Returns:
            CVintraResult or None if extraction fails
            
        Example:
            >>> from backend.models.llm_handler import get_llm
            >>> llm_handler = get_llm()
            >>> llm_extractor = CVintraLLMExtractor(llm_handler)
            >>> result = llm_extractor.extract_cvintra(abstract)
        """
```

### CVintraValidator

```python
from backend.llm.cvintra_extractor import CVintraValidator

class CVintraValidator:
    
    MIN_CV: float = 5.0
    MAX_CV: float = 100.0
    MIN_CONFIDENCE: float = 0.3
    
    @staticmethod
    def is_valid(result: CVintraResult) -> bool:
        """Check if result is valid"""
    
    @staticmethod
    def aggregate_results(
        results: List[CVintraResult],
        method: str = "weighted_mean"
    ) -> Tuple[Optional[float], float, List[Dict[str, Any]]]:
        """
        Aggregate multiple CVintra results.
        
        Args:
            results: List of CVintraResult objects
            method: "weighted_mean" | "median" | "mean"
            
        Returns:
            (aggregated_value, confidence, sources_list)
            
        Example:
            >>> agg_val, conf, sources = CVintraValidator.aggregate_results(
            ...     results, method="weighted_mean"
            ... )
        """
```

### CVintraExtractor (Main Pipeline)

```python
from backend.llm.cvintra_extractor import CVintraExtractor

class CVintraExtractor:
    
    def __init__(self, llm_handler=None, use_llm_fallback: bool = True):
        """Initialize hybrid extraction pipeline."""
    
    def extract(
        self,
        text: str,
        pmid: str = "",
        url: str = "",
        use_llm: bool = True
    ) -> List[CVintraResult]:
        """
        Extract CVintra using hybrid regex + LLM approach.
        
        Pipeline:
        1. Try regex (fast, 50-100ms)
        2. If no match or low confidence, try LLM (fallback)
        
        Args:
            text: Article text or abstract
            pmid: PubMed ID
            url: Source URL
            use_llm: Enable LLM fallback
            
        Returns:
            List of results sorted by confidence
            
        Example:
            >>> extractor = CVintraExtractor(use_llm_fallback=False)
            >>> results = extractor.extract(abstract)
            >>> for r in results:
            ...     print(f"{r.cvintra}% (confidence={r.confidence})")
        """
    
    def extract_from_articles(
        self,
        articles: List[Dict[str, str]],
        use_llm: bool = True
    ) -> Tuple[Optional[float], float, List[Dict[str, Any]], List[CVintraResult]]:
        """
        Extract CVintra from multiple articles and aggregate.
        
        Args:
            articles: List of dicts with keys:
                     {pmid, title, abstract, url}
            use_llm: Enable LLM fallback
            
        Returns:
            (aggregated_value, confidence, sources, all_results)
            
        Example:
            >>> articles = [
            ...     {
            ...         'pmid': '123',
            ...         'title': 'Study Title',
            ...         'abstract': 'Article abstract...',
            ...         'url': 'https://...'
            ...     }
            ... ]
            >>> val, conf, sources, results = extractor.extract_from_articles(
            ...     articles, use_llm=False
            ... )
            >>> print(f"CVintra: {val}% (confidence: {conf:.2f})")
        """
```

---

## Scraper Classes

### CacheManager

```python
from backend.scrapers.pubmed_scraper import CacheManager

class CacheManager:
    
    def __init__(self, db_path: str = "backend/cache/pubmed_cache.db"):
        """Initialize SQLite3 cache database."""
    
    # Article caching
    def cache_article(
        self,
        pmid: str,
        title: str,
        abstract: str,
        authors: List[str],
        year: int,
        url: str,
        article_type: str = "other"
    ) -> None:
        """Cache article metadata."""
    
    def get_article(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached article."""
    
    # CVintra extraction caching
    def cache_cvintra(
        self,
        pmid: str,
        cvintra: Optional[float],
        confidence: float,
        method: str,
        evidence: str,
        sources: List[Dict],
        drug_name: str = ""
    ) -> None:
        """Cache CVintra extraction."""
    
    def get_cvintra(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached CVintra extraction."""
    
    # Query result caching
    def cache_query_result(
        self,
        drug_name: str,
        result: Dict,
        ttl_hours: int = 24
    ) -> None:
        """Cache complete query result (with TTL)."""
    
    def get_query_result(
        self,
        drug_name: str,
        max_age_hours: int = 24
    ) -> Optional[Dict]:
        """Retrieve cached query result if not expired."""
    
    # Maintenance
    def clear_old_entries(self, days: int = 30) -> None:
        """Clear cache entries older than specified days."""
```

### ArticleDeduplicator

```python
from backend.scrapers.pubmed_scraper import ArticleDeduplicator

class ArticleDeduplicator:
    
    @staticmethod
    def normalize_title(title: str) -> str:
        """Remove special chars, normalize case."""
    
    @staticmethod
    def similarity_score(title1: str, title2: str) -> float:
        """Jaccard similarity coefficient (0-1)."""
    
    @staticmethod
    def deduplicate(
        articles: List[Dict[str, Any]],
        threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate articles.
        
        Args:
            articles: List of article dicts with 'title', 'year'
            threshold: Similarity threshold for grouping
            
        Returns:
            Deduplicated list (keeps most recent per group)
            
        Example:
            >>> articles = [...]
            >>> unique = ArticleDeduplicator.deduplicate(articles)
        """
```

### SourceRanker

```python
from backend.scrapers.pubmed_scraper import SourceRanker

class SourceRanker:
    
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
        """
        Calculate overall reliability score (0-1).
        
        Weighted factors:
        - Article type: 35%
        - Subject type: 25%
        - Method: 20%
        - Confidence: 15%
        - Recency: 5%
        """
    
    @staticmethod
    def rank_sources(
        sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rank and sort sources by reliability.
        
        Example:
            >>> ranked = SourceRanker.rank_sources(sources)
            >>> for i, source in enumerate(ranked, 1):
            ...     print(f"{i}. {source['reliability_score']:.2f}")
        """
```

### PubMedScraper (Enhanced)

```python
from backend.scrapers.pubmed_scraper import PubMedScraper

class PubMedScraper:
    
    def __init__(
        self,
        email: str = None,
        api_key: str = None,
        use_cache: bool = True,
        use_llm: bool = True
    ):
        """
        Initialize PubMed scraper with all features.
        
        Args:
            email: NCBI email (required)
            api_key: NCBI API key (optional, 10 req/sec)
            use_cache: Enable SQLite caching
            use_llm: Enable LLM fallback for extraction
        """
    
    def get_drug_pk_data(self, inn: str) -> dict:
        """
        Full production pipeline for CVintra extraction.
        
        Pipeline:
        1. Check query cache (24h TTL)
        2. Search PubMed
        3. Fetch articles (with caching)
        4. Classify articles
        5. Deduplicate
        6. Extract CVintra (hybrid)
        7. Rank sources
        8. Aggregate
        9. Cache result
        
        Args:
            inn: Drug name (INN or common name)
            
        Returns:
            {
                "drug": str,
                "status": "success" | "not_found" | "error",
                "n_articles": int,
                "cvintra": float | None,
                "cvintra_confidence": float,
                "articles": [...],
                "sources": [...],
                "pk_parameters": {...},
                "timestamp": str
            }
            
        Example:
            >>> scraper = PubMedScraper(use_cache=True)
            >>> result = scraper.get_drug_pk_data("aspirin")
            >>> print(f"CVintra: {result['cvintra']}%")
        """
    
    def search_drug(self, inn: str, keywords: list = None) -> list:
        """Search PubMed for drug articles."""
    
    def fetch_article_details(self, pmid: str) -> dict:
        """Fetch article by PMID."""
    
    def _classify_article(self, title: str, abstract: str) -> Tuple[str, str]:
        """Classify article type and subject (human/animal)."""
    
    def _extract_year(self, year_str: str) -> int:
        """Parse year from string."""
    
    def extract_pk_parameters(self, articles: list) -> dict:
        """Extract PK parameters (Cmax, AUC, etc) using regex."""
```

---

## Usage Examples

### Example 1: Simple Extraction

```python
from backend.scrapers.pubmed_scraper import PubMedScraper

scraper = PubMedScraper(email="your.email@example.com")
result = scraper.get_drug_pk_data("aspirin")

print(f"CVintra: {result['cvintra']}%")
print(f"Confidence: {result['cvintra_confidence']:.2f}")
print(f"Found {result['n_articles']} articles")
```

### Example 2: Custom Regex Extraction

```python
from backend.llm.cvintra_extractor import CVintraRegexExtractor

extractor = CVintraRegexExtractor()

text = "The intra-subject CVintra for Cmax was 22.5%."
results = extractor.extract_cvintra(text, pmid="123")

for result in results:
    print(f"Value: {result.cvintra}%")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Evidence: {result.evidence}")
```

### Example 3: Multi-Article Aggregation

```python
from backend.llm.cvintra_extractor import CVintraExtractor

extractor = CVintraExtractor(use_llm_fallback=False)

articles = [
    {"pmid": "1", "title": "Study 1", "abstract": "...", "url": "..."},
    {"pmid": "2", "title": "Study 2", "abstract": "...", "url": "..."},
]

agg_value, confidence, sources, results = extractor.extract_from_articles(
    articles, use_llm=False
)

print(f"Aggregated: {agg_value}% (confidence: {confidence:.2f})")
print(f"From {len(sources)} sources")
```

### Example 4: Cache Management

```python
scraper = PubMedScraper(use_cache=True)

# First query (slow, hits API)
result1 = scraper.get_drug_pk_data("aspirin")  # 15-30 seconds

# Same query (fast, from cache)
result2 = scraper.get_drug_pk_data("aspirin")  # <1 second

# Clear old cache
scraper.cache.clear_old_entries(days=30)
```

### Example 5: Source Ranking

```python
from backend.scrapers.pubmed_scraper import SourceRanker

sources = result["sources"]
ranked = SourceRanker.rank_sources(sources)

for i, source in enumerate(ranked, 1):
    print(f"{i}. Score={source['reliability_score']:.2f}")
    print(f"   Type={source['article_type']}")
    print(f"   Value={source['value']}%")
```

---

## Error Handling

### Graceful Degradation

```python
try:
    scraper = PubMedScraper(use_llm=True)
except ImportError:
    # LLM not available, fall back to regex
    scraper = PubMedScraper(use_llm=False)

result = scraper.get_drug_pk_data("aspirin")

if result["status"] == "success":
    print(f"CVintra: {result['cvintra']}%")
elif result["status"] == "error":
    print(f"Error: {result.get('error')}")
else:  # not_found
    print("No articles found for this drug")
```

### Confidence Thresholds

```python
result = scraper.get_drug_pk_data("aspirin")

if result["cvintra_confidence"] >= 0.9:
    print("Very high confidence result")
elif result["cvintra_confidence"] >= 0.7:
    print("Good confidence result")
elif result["cvintra_confidence"] >= 0.5:
    print("Moderate confidence, verify manually")
else:
    print("Low confidence, use with caution")
```

---

## Extension Points

### Add Custom Regex Patterns

```python
from backend.llm.cvintra_extractor import CVintraRegexExtractor

# Add to the CV_PATTERNS list
CVintraRegexExtractor.CV_PATTERNS.append(
    (r'your_custom_pattern', 0.90)  # (pattern, confidence)
)
```

### Modify LLM Prompt

```python
from backend.llm.cvintra_extractor import CVintraLLMExtractor

CVintraLLMExtractor.SYSTEM_PROMPT = """Your custom prompt here"""
```

### Custom Ranking Algorithm

```python
from backend.scrapers.pubmed_scraper import SourceRanker

class CustomRanker(SourceRanker):
    @staticmethod
    def calculate_score(source):
        # Your custom logic
        return score
```

---

## Environment Variables

```bash
# Required
NCBI_EMAIL=your.email@example.com

# Optional
NCBI_API_KEY=your_api_key              # Increases rate limit
HF_MODEL=mistralai/Mistral-7B-Instruct # LLM model
HF_TOKEN=your_huggingface_token        # HuggingFace token
```

---

## Logging

```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

# Log everything from pipeline
logger = logging.getLogger('backend.llm.cvintra_extractor')
logger.setLevel(logging.DEBUG)
```

---

## Performance Tips

1. **Enable caching**: Use `PubMedScraper(use_cache=True)`
2. **Use API key**: Speeds up PubMed queries (3→10 req/sec)
3. **Disable LLM**: Faster if you don't need advanced extraction
4. **Batch processing**: Process multiple drugs at once
5. **Monitor cache size**: Clear old entries regularly

---

## Reference Links

- [PubMed API Docs](https://www.ncbi.nlm.nih.gov/books/NBK25499/)
- [BioPython Docs](https://biopython.org/)
- [NCBI FAQ](https://www.ncbi.nlm.nih.gov/grc/faq/)
