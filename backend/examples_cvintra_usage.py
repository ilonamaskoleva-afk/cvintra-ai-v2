"""
CVintra Extraction Pipeline - Usage Examples

This file demonstrates practical usage of the production-ready CVintra extraction system.
"""

# ============================================================================
# EXAMPLE 1: Basic CVintra Extraction from Text
# ============================================================================

from backend.llm.cvintra_extractor import CVintraRegexExtractor

# Initialize extractor
extractor = CVintraRegexExtractor()

# Sample abstract
abstract = """
A randomized, crossover bioavailability study was conducted in healthy volunteers.
The pharmacokinetic parameters were analyzed. CVintra (intra-subject coefficient of 
variation) for Cmax was 22.3% and for AUC was 18.5%, indicating moderate within-subject
variability. The study included 24 subjects.
"""

# Extract CVintra
results = extractor.extract_cvintra(abstract, pmid="12345678", url="https://pubmed.ncbi.nlm.nih.gov/12345678")

print("=" * 60)
print("EXAMPLE 1: Basic CVintra Extraction")
print("=" * 60)

if results:
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  CVintra: {result.cvintra}%")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Method: {result.method}")
        print(f"  Evidence: {result.evidence[:60]}...")
else:
    print("No CVintra values found")


# ============================================================================
# EXAMPLE 2: Article Deduplication
# ============================================================================

from backend.scrapers.pubmed_scraper import ArticleDeduplicator

print("\n" + "=" * 60)
print("EXAMPLE 2: Article Deduplication")
print("=" * 60)

articles = [
    {
        "pmid": "1",
        "title": "Bioavailability and Pharmacokinetics of Aspirin in Healthy Volunteers",
        "year": 2022,
    },
    {
        "pmid": "2",
        "title": "Bioavailability and pharmacokinetics of aspirin in healthy volunteers: a randomized crossover study",
        "year": 2023,
    },
    {
        "pmid": "3",
        "title": "Safety Profile of Acetaminophen in Pediatric Patients",
        "year": 2022,
    },
    {
        "pmid": "4",
        "title": "Clinical Pharmacology of Metformin: A Systematic Review",
        "year": 2021,
    },
]

print(f"\nBefore deduplication: {len(articles)} articles")
for article in articles:
    print(f"  {article['pmid']}: {article['title'][:50]}...")

deduplicated = ArticleDeduplicator.deduplicate(articles, threshold=0.85)

print(f"\nAfter deduplication: {len(deduplicated)} articles")
for article in deduplicated:
    print(f"  {article['pmid']}: {article['title'][:50]}...")


# ============================================================================
# EXAMPLE 3: Source Ranking
# ============================================================================

from backend.scrapers.pubmed_scraper import SourceRanker

print("\n" + "=" * 60)
print("EXAMPLE 3: Source Ranking by Reliability")
print("=" * 60)

sources = [
    {
        "pmid": "100001",
        "url": "https://pubmed.ncbi.nlm.nih.gov/100001",
        "method": "regex",
        "value": 20.5,
        "confidence": 0.95,
        "article_type": "clinical_trial",
        "subject_type": "human",
        "year": 2023,
    },
    {
        "pmid": "100002",
        "url": "https://pubmed.ncbi.nlm.nih.gov/100002",
        "method": "llm",
        "value": 19.8,
        "confidence": 0.75,
        "article_type": "review",
        "subject_type": "human",
        "year": 2021,
    },
    {
        "pmid": "100003",
        "url": "https://pubmed.ncbi.nlm.nih.gov/100003",
        "method": "regex",
        "value": 22.1,
        "confidence": 0.85,
        "article_type": "other",
        "subject_type": "animal",
        "year": 2022,
    },
]

ranked = SourceRanker.rank_sources(sources)

print("\nSources ranked by reliability:")
for i, source in enumerate(ranked, 1):
    print(f"\n{i}. PMID {source['pmid']}")
    print(f"   CVintra: {source['value']}%")
    print(f"   Article type: {source['article_type']}")
    print(f"   Subject type: {source['subject_type']}")
    print(f"   Year: {source['year']}")
    print(f"   Reliability score: {source['reliability_score']:.2f}")


# ============================================================================
# EXAMPLE 4: CVintra Extraction from Multiple Articles
# ============================================================================

from backend.llm.cvintra_extractor import CVintraExtractor

print("\n" + "=" * 60)
print("EXAMPLE 4: Aggregating CVintra from Multiple Articles")
print("=" * 60)

# Sample articles
mock_articles = [
    {
        "pmid": "200001",
        "title": "Bioavailability of Drug A",
        "abstract": "The intra-subject CV for Cmax was 18.5% and for AUC was 15.2%.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/200001",
    },
    {
        "pmid": "200002",
        "title": "Pharmacokinetics of Drug A in Humans",
        "abstract": "Within-subject coefficient of variation was 22.3%.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/200002",
    },
    {
        "pmid": "200003",
        "title": "Drug A Clinical Study",
        "abstract": "CVintra = 20.1% with a 95% CI.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/200003",
    },
]

# Extract using hybrid pipeline (regex only for this example)
extractor = CVintraExtractor(use_llm_fallback=False)

agg_value, confidence, sources, all_results = extractor.extract_from_articles(
    mock_articles, use_llm=False
)

print(f"\nExtraction from {len(mock_articles)} articles:")
print(f"  Aggregated CVintra: {agg_value}%")
print(f"  Aggregation confidence: {confidence:.2f}")
print(f"  Number of sources: {len(sources)}")

print(f"\nDetailed extraction results:")
for source in sources:
    print(f"  PMID {source['pmid']}: {source['value']}% | {source['method']} | confidence={source['confidence']:.2f}")


# ============================================================================
# EXAMPLE 5: Cache Management
# ============================================================================

from backend.scrapers.pubmed_scraper import CacheManager

print("\n" + "=" * 60)
print("EXAMPLE 5: Cache Management")
print("=" * 60)

cache = CacheManager(db_path="backend/cache/example_cache.db")

# Cache an article
print("\nCaching article...")
cache.cache_article(
    pmid="300001",
    title="Example Article on CVintra Extraction",
    abstract="This is an example abstract for caching purposes.",
    authors=["Smith J", "Johnson M", "Williams A"],
    year=2023,
    url="https://pubmed.ncbi.nlm.nih.gov/300001",
    article_type="clinical_trial",
)
print("Article cached successfully")

# Retrieve from cache
print("Retrieving from cache...")
cached_article = cache.get_article("300001")
if cached_article:
    print(f"Found: {cached_article['title']}")
    print(f"Year: {cached_article['year']}")
    print(f"Authors: {', '.join(cached_article['authors'])}")
else:
    print("Article not found in cache")

# Cache CVintra extraction
print("\nCaching CVintra extraction...")
cache.cache_cvintra(
    pmid="300001",
    cvintra=20.5,
    confidence=0.92,
    method="regex",
    evidence="The intra-subject CV was 20.5% in this study.",
    sources=[{"url": "https://pubmed.ncbi.nlm.nih.gov/300001", "method": "regex"}],
    drug_name="Drug A",
)
print("CVintra extraction cached")

# Retrieve CVintra from cache
print("Retrieving CVintra from cache...")
cached_cvintra = cache.get_cvintra("300001")
if cached_cvintra:
    print(f"CVintra: {cached_cvintra['cvintra']}%")
    print(f"Confidence: {cached_cvintra['confidence']:.2f}")
    print(f"Method: {cached_cvintra['method']}")
else:
    print("CVintra not found in cache")


# ============================================================================
# EXAMPLE 6: Article Classification
# ============================================================================

from backend.scrapers.pubmed_scraper import PubMedScraper
import re

print("\n" + "=" * 60)
print("EXAMPLE 6: Article Classification")
print("=" * 60)

# Create scraper instance (just for classification methods)
scraper = PubMedScraper(use_cache=False, use_llm=False)

test_articles = [
    {
        "title": "A Randomized, Double-Blind, Placebo-Controlled Bioequivalence Study",
        "abstract": "This clinical trial evaluated bioavailability in healthy human volunteers.",
    },
    {
        "title": "Systematic Review of CVintra Variations",
        "abstract": "A meta-analysis was performed on published pharmacokinetic studies.",
    },
    {
        "title": "In Vitro Metabolism of Drug A",
        "abstract": "The drug was metabolized in rat liver microsomes.",
    },
]

print("\nClassifying articles:")
for i, article in enumerate(test_articles, 1):
    article_type, subject_type = scraper._classify_article(
        article["title"], article["abstract"]
    )
    print(f"\nArticle {i}:")
    print(f"  Type: {article_type}")
    print(f"  Subject: {subject_type}")
    print(f"  Title: {article['title'][:50]}...")


# ============================================================================
# EXAMPLE 7: Full Production Pipeline
# ============================================================================

print("\n" + "=" * 60)
print("EXAMPLE 7: Full Production Pipeline")
print("=" * 60)

print("""
To use the full production pipeline with real PubMed data:

1. Set up environment variables:
   export NCBI_EMAIL="your.email@example.com"
   export NCBI_API_KEY="your_api_key"  # Optional

2. Initialize scraper:
   from backend.scrapers.pubmed_scraper import PubMedScraper
   
   scraper = PubMedScraper(
       use_cache=True,       # Enable SQLite caching
       use_llm=False         # Set to True if GPU available
   )

3. Extract CVintra:
   result = scraper.get_drug_pk_data("aspirin")
   
   print(result)

4. Response includes:
   - drug: str (drug name)
   - status: "success" | "not_found" | "error"
   - n_articles: int (number of articles processed)
   - cvintra: float | null (aggregated value)
   - cvintra_confidence: float (0-1)
   - sources: list (ranked by reliability)
   - articles: list (article metadata)
   - pk_parameters: dict (legacy extraction)
   - timestamp: str (ISO format)

5. Cache benefits:
   - First query: 10-30 seconds
   - Cached query: <1 second
   - Cache TTL: 24 hours
""")

print("=" * 60)
print("\nFor more information, see: backend/llm/CVINTRA_PIPELINE_README.md")
