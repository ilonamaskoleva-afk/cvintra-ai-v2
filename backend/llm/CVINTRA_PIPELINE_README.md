# CVintra Extraction Pipeline

Production-ready hybrid extraction system for intra-subject coefficient of variation (CVintra) from PubMed articles.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PubMed Scraper                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Query Cache (24h TTL)                                       │
│  2. Article Fetching (via Entrez API)                          │
│  3. Article Classification (clinical trial, review, etc.)      │
│  4. Deduplication (title-based similarity)                     │
│  5. CVintra Extraction (hybrid regex + LLM)                    │
│  6. Source Ranking (reliability scoring)                        │
│  7. Aggregation (weighted average)                             │
└─────────────────────────────────────────────────────────────────┘
              │
              ├─► CacheManager (SQLite)
              │   - Articles cache
              │   - CVintra extractions
              │   - Query results
              │
              ├─► CVintraExtractor (Hybrid Pipeline)
              │   ├─► CVintraRegexExtractor (fast, high-precision)
              │   └─► CVintraLLMExtractor (fallback, advanced comprehension)
              │
              └─► Supporting Classes
                  ├─► ArticleDeduplicator
                  └─► SourceRanker
```

## Features

### 1. **Hybrid Extraction Pipeline**
- **Regex-first approach** (0.7-0.95 confidence) for fast, reliable standard formats
- **LLM fallback** for complex/non-standard text patterns
- Automatic validation (5-100% range)
- Evidence tracking with exact sentence extraction

### 2. **Production Optimizations**
- ✅ **SQLite Caching** - 24h TTL for queries, article metadata, extractions
- ✅ **Article Deduplication** - Word-based similarity (threshold: 0.85)
- ✅ **Source Ranking** - Reliability scoring based on:
  - Article type (clinical trial > review > other)
  - Subject type (human > animal > in vitro)
  - Extraction method confidence
  - Publication recency
- ✅ **Confidence Weighting** - Aggregation using weighted average
- ✅ **Error Handling** - Graceful degradation, detailed logging

### 3. **Extraction Methods**

#### Regex Patterns (15+ patterns)
```
Standard:
- "CVintra = 25.5%"
- "intra-subject CV: 25.5%"

Alternative names:
- "within-subject CV = 25.5%"
- "intra-individual variability: 25.5%"

Table formats:
- "CVw = 25.5%"
- "CV_w: 25.5%"
```

#### LLM Extraction
Uses specialized pharmacokinetics prompt for:
- Complex sentence structures
- Implicit CVintra mentions
- Multiple PK parameters in text
- Table extraction

## Installation

### Prerequisites
```bash
pip install biopython requests beautifulsoup4
```

### Optional (for LLM features)
```bash
pip install transformers torch  # Mistral-7B
```

## Usage

### Basic Usage

```python
from backend.scrapers.pubmed_scraper import PubMedScraper

# Initialize scraper
scraper = PubMedScraper(
    email="your.email@example.com",  # Required for NCBI
    api_key="your_api_key",           # Optional, increases rate limit
    use_cache=True,                   # Enable caching
    use_llm=False                     # Set to True if LLM available
)

# Extract CVintra
result = scraper.get_drug_pk_data("aspirin")

print(result)
```

### Response Format

```json
{
  "drug": "aspirin",
  "status": "success",
  "n_articles": 12,
  "cvintra": 20.5,
  "cvintra_confidence": 0.89,
  "articles": [
    {
      "pmid": "12345678",
      "title": "Bioavailability of Aspirin...",
      "year": 2023,
      "url": "https://pubmed.ncbi.nlm.nih.gov/12345678",
      "article_type": "clinical_trial",
      "subject_type": "human"
    }
  ],
  "sources": [
    {
      "pmid": "12345678",
      "url": "https://pubmed.ncbi.nlm.nih.gov/12345678",
      "method": "regex",
      "value": 20.5,
      "confidence": 0.95,
      "article_type": "clinical_trial",
      "subject_type": "human",
      "year": 2023,
      "reliability_score": 0.92
    }
  ],
  "pk_parameters": {
    "cxintra": {"value": 20.5, "sources": [...]},
    "cmax": {"value": 1500, "unit": "ng/mL", "sources": [...]},
    "auc": {"value": 2400, "unit": "ng·h/mL", "sources": [...]}
  },
  "timestamp": "2024-02-20T15:30:45.123456"
}
```

## Advanced Features

### 1. Cache Management

```python
# Clear old cache entries
scraper.cache.clear_old_entries(days=30)

# Access cache directly
article = scraper.cache.get_article("12345678")
cvintra = scraper.cache.get_cvintra("12345678")
```

### 2. Article Classification

Automatically detects:
- **Article Types**: clinical_trial, review, observational, methodology, other
- **Subject Types**: human, animal, in_vitro

```python
article_type, subject_type = scraper._classify_article(title, abstract)
```

### 3. Source Ranking

Scores sources based on:
- Article reliability (0.35 weight)
- Subject relevance (0.25 weight)
- Extraction method (0.20 weight)
- Extraction confidence (0.15 weight)
- Publication recency (0.05 weight)

```python
from backend.scrapers.pubmed_scraper import SourceRanker

ranked_sources = SourceRanker.rank_sources(sources)
```

### 4. Regex Extraction Directly

```python
from backend.llm.cvintra_extractor import CVintraRegexExtractor

extractor = CVintraRegexExtractor()
results = extractor.extract_cvintra(abstract_text, pmid="12345")

for result in results:
    print(f"CVintra: {result.cvintra}%")
    print(f"Confidence: {result.confidence}")
    print(f"Evidence: {result.evidence}")
```

### 5. LLM-Based Extraction

```python
from backend.llm.cvintra_extractor import CVintraLLMExtractor
from backend.models.llm_handler import get_llm

llm_handler = get_llm()
llm_extractor = CVintraLLMExtractor(llm_handler=llm_handler)

result = llm_extractor.extract_cvintra(abstract_text)
```

## Testing

Run integration tests:
```bash
python backend/test_cvintra_integration.py
```

Tests include:
1. ✓ Regex extraction patterns
2. ✓ Article deduplication
3. ✓ Source ranking
4. ✓ Cache operations
5. ✓ CVintra extractor pipeline
6. ✓ Full scraper integration

## Performance

### Benchmarks (per article with regex only)
- Article fetch: ~1-2s
- CVintra extraction: ~50-100ms
- Deduplication: ~10-50ms
- Source ranking: ~5-10ms
- **Total for 10 articles**: ~12-25s (with API rate limits)

### Caching Benefits
- Cache hit: ~10-50ms (vs 12-25s)
- Query cache TTL: 24 hours
- Article cache: 30 days retention

## Configuration

**Environment Variables** (.env file):
```
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=your_ncbi_api_key
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2
HF_TOKEN=your_huggingface_token
CACHE_DB_PATH=backend/cache/pubmed_cache.db
```

## Data Quality

### Validation Rules
- CVintra range: 5-100%
- Confidence threshold: > 0.3
- Duplicate articles: similarity > 0.85 (removed)
- Source requires valid evidence

### Error Handling
All errors are logged with:
- Function name
- Input parameters (sanitized)
- Exception details
- Graceful fallback to next method

## Extensibility

### Adding Custom Regex Patterns
```python
# In CVintraRegexExtractor.CV_PATTERNS
(r'your_pattern', 0.90),  # (pattern, confidence)
```

### Adding Custom LLM Prompts
```python
# Modify CVintraLLMExtractor.SYSTEM_PROMPT
SYSTEM_PROMPT = """Your custom prompt..."""
```

### Adding New Classification Rules
```python
# In PubMedScraper.__init__
self.custom_patterns = [r'pattern1', r'pattern2']
```

## Production Deployment

### Recommended Settings
```python
scraper = PubMedScraper(
    use_cache=True,           # Enable if persistent storage available
    use_llm=False,            # Disable if GPU memory limited
    api_key="your_key"        # Essential for high volume
)

# Clear cache regularly
scraper.cache.clear_old_entries(days=30)

# Log monitoring
logging.basicConfig(level=logging.INFO)
```

### Rate Limiting
- Without API key: 3 requests/second
- With API key: 10 requests/second
- Automatic delays between requests

## Future Improvements

- [ ] Async/concurrent API requests
- [ ] Redis caching backend
- [ ] MLFlow experiment tracking
- [ ] Multi-language support
- [ ] Confidence interval estimation
- [ ] InterLLM routing (OpenAI, Claude, etc.)

## License

Proprietary - Medical BioTech Research

## References

1. NCBI Entrez API: https://www.ncbi.nlm.nih.gov/books/NBK25499/
2. BioPython Tutorial: https://biopython.org/wiki/Documentation
3. Pharmacokinetics Standards: https://www.ema.europa.eu/
