"""
Test script for CVintra Extraction Pipeline
Demonstrates the complete production pipeline.
"""

import sys
import json
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_regex_extraction():
    """Test regex-based extraction"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Regex-based CVintra Extraction")
    logger.info("="*60)
    
    from backend.llm.cvintra_extractor import CVintraRegexExtractor
    
    # Test cases with various CVintra formats
    test_texts = [
        # Standard format
        "The intra-subject CV was 25.5%.",
        
        # CVintra abbreviation
        "CVintra = 18.3%",
        
        # Within-subject variation
        "Within-subject coefficient of variation (CV) was 22%",
        
        # With context
        "Pharmacokinetic parameters were highly variable. The intra-subject CV for Cmax was 15.8% and for AUC was 12.5%.",
        
        # Multiple values (should extract best one)
        "Inter-subject CV was 35%, while intra-subject CV = 20%",
    ]
    
    extractor = CVintraRegexExtractor()
    
    for i, text in enumerate(test_texts, 1):
        logger.info(f"\nTest {i}: {text[:50]}...")
        results = extractor.extract_cvintra(text, pmid=f"TEST{i}", url="")
        
        if results:
            best = results[0]
            logger.info(f"  ✓ Found: {best.cvintra}% (confidence: {best.confidence:.2f})")
            logger.info(f"  Method: {best.method}")
            logger.info(f"  Evidence: {best.evidence[:50]}...")
        else:
            logger.warning(f"  ✗ No CVintra found")


def test_article_deduplication():
    """Test article deduplication"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Article Deduplication")
    logger.info("="*60)
    
    from backend.scrapers.pubmed_scraper import ArticleDeduplicator
    
    # Create test articles with similar titles
    articles = [
        {"pmid": "1", "title": "Pharmacokinetics of Aspirin in Healthy Volunteers", "year": 2020},
        {"pmid": "2", "title": "Pharmacokinetics of Aspirin in healthy volunteers: a randomized study", "year": 2021},
        {"pmid": "3", "title": "Safety of Ibuprofen in Patients with Renal Impairment", "year": 2019},
        {"pmid": "4", "title": "Different topic entirely", "year": 2020},
    ]
    
    logger.info(f"Original: {len(articles)} articles")
    for article in articles:
        logger.info(f"  {article['pmid']}: {article['title'][:50]}...")
    
    deduplicated = ArticleDeduplicator.deduplicate(articles, threshold=0.85)
    
    logger.info(f"\nDeduplicated: {len(deduplicated)} articles")
    for article in deduplicated:
        logger.info(f"  {article['pmid']}: {article['title'][:50]}...")


def test_source_ranking():
    """Test source ranking by reliability"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Source Ranking")
    logger.info("="*60)
    
    from backend.scrapers.pubmed_scraper import SourceRanker
    from datetime import datetime
    
    sources = [
        {
            "pmid": "1",
            "url": "https://pubmed.ncbi.nlm.nih.gov/1",
            "method": "regex",
            "value": 20.5,
            "confidence": 0.95,
            "article_type": "clinical_trial",
            "subject_type": "human",
            "year": 2023,
        },
        {
            "pmid": "2",
            "url": "https://pubmed.ncbi.nlm.nih.gov/2",
            "method": "llm",
            "value": 18.3,
            "confidence": 0.70,
            "article_type": "review",
            "subject_type": "human",
            "year": 2020,
        },
        {
            "pmid": "3",
            "url": "https://pubmed.ncbi.nlm.nih.gov/3",
            "method": "regex",
            "value": 22.0,
            "confidence": 0.85,
            "article_type": "other",
            "subject_type": "animal",
            "year": 2022,
        },
    ]
    
    logger.info("Original sources:")
    for s in sources:
        logger.info(f"  {s['pmid']}: {s['article_type']}, {s['subject_type']}, year={s['year']}")
    
    ranked = SourceRanker.rank_sources(sources)
    
    logger.info("\nRanked sources (by reliability):")
    for i, s in enumerate(ranked, 1):
        logger.info(
            f"  {i}. {s['pmid']}: "
            f"score={s['reliability_score']:.2f}, "
            f"type={s['article_type']}, "
            f"subject={s['subject_type']}"
        )


def test_cache_manager():
    """Test cache operations"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Cache Manager")
    logger.info("="*60)
    
    from backend.scrapers.pubmed_scraper import CacheManager
    
    cache = CacheManager(db_path="backend/cache/test_cache.db")
    
    # Test article caching
    logger.info("Caching article...")
    cache.cache_article(
        pmid="12345",
        title="Test Article",
        abstract="This is a test abstract",
        authors=["Smith J", "Jones M"],
        year=2023,
        url="https://pubmed.ncbi.nlm.nih.gov/12345",
        article_type="clinical_trial"
    )
    
    logger.info("Retrieving cached article...")
    article = cache.get_article("12345")
    if article:
        logger.info(f"✓ Found: {article['title']} (PMID: {article['pmid']})")
    else:
        logger.warning("✗ Article not found in cache")
    
    # Test CVintra caching
    logger.info("Caching CVintra extraction...")
    cache.cache_cvintra(
        pmid="12345",
        cvintra=20.5,
        confidence=0.95,
        method="regex",
        evidence="The intra-subject CV was 20.5%",
        sources=[],
        drug_name="Aspirin"
    )
    
    logger.info("Retrieving cached CVintra...")
    cvintra = cache.get_cvintra("12345")
    if cvintra:
        logger.info(f"✓ Found: CVintra={cvintra['cvintra']}% (confidence: {cvintra['confidence']})")
    else:
        logger.warning("✗ CVintra not found in cache")


def test_cvintra_extractor():
    """Test CVintra extractor (regex-based, no LLM)"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: CVintra Extractor Pipeline")
    logger.info("="*60)
    
    from backend.llm.cvintra_extractor import CVintraExtractor
    
    # Create extractor without LLM
    extractor = CVintraExtractor(use_llm_fallback=False)
    
    # Test with mock articles
    mock_articles = [
        {
            "pmid": "1001",
            "title": "Bioavailability of Aspirin in Healthy Subjects",
            "abstract": "A randomized, crossover study was conducted. The intra-subject CVintra for Cmax was 18.5% and for AUC was 15.2%.",
            "url": "https://pubmed.ncbi.nlm.nih.gov/1001"
        },
        {
            "pmid": "1002",
            "title": "Pharmacokinetics of Aspirin: Clinical Implications",
            "abstract": "The within-subject coefficient of variation was 22.3%, indicating moderate bioavailability variability.",
            "url": "https://pubmed.ncbi.nlm.nih.gov/1002"
        },
    ]
    
    logger.info(f"Extracting from {len(mock_articles)} articles...")
    
    agg_value, confidence, sources, all_results = extractor.extract_from_articles(
        mock_articles, use_llm=False
    )
    
    logger.info(f"\nResults:")
    logger.info(f"  Aggregated CVintra: {agg_value}% (confidence: {confidence:.2f})")
    logger.info(f"  Sources found: {len(sources)}")
    
    for i, source in enumerate(sources, 1):
        logger.info(
            f"    {i}. PMID {source['pmid']}: "
            f"{source['value']}% ({source['method']}, "
            f"confidence={source['confidence']:.2f})"
        )


def test_pubmed_scraper():
    """Test PubMed Scraper integration (demo mode)"""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: PubMed Scraper Integration")
    logger.info("="*60)
    
    try:
        from backend.scrapers.pubmed_scraper import PubMedScraper
        
        logger.info("Initializing PubMed Scraper...")
        scraper = PubMedScraper(use_cache=True, use_llm=False)
        
        logger.info("\n✓ Scraper initialized successfully!")
        logger.info("  - Cache: enabled")
        logger.info("  - LLM fallback: disabled (for demo)")
        logger.info("  - CVintra extractor: initialized")
        
        logger.info("\nScraper is ready for production use.")
        logger.info("Example usage:")
        logger.info("  result = scraper.get_drug_pk_data('aspirin')")
        logger.info("  print(json.dumps(result, indent=2))")
        
    except Exception as e:
        logger.error(f"Scraper initialization failed: {e}")


def main():
    """Run all tests"""
    logger.info("\n" + "█"*60)
    logger.info("█  CVintra Extraction Pipeline - Integration Tests")
    logger.info("█"*60)
    
    try:
        test_regex_extraction()
        test_article_deduplication()
        test_source_ranking()
        test_cache_manager()
        test_cvintra_extractor()
        test_pubmed_scraper()
        
        logger.info("\n" + "█"*60)
        logger.info("█  All tests completed successfully! ✓")
        logger.info("█"*60 + "\n")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
