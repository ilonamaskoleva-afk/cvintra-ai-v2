"""
CVintra (Intra-subject Coefficient of Variation) Extraction Pipeline

Hybrid approach combining:
1. Regex-based extraction (fast, high precision)
2. LLM-based extraction (fall-back for complex cases)
3. Validation and confidence scoring
4. Deduplication and aggregation
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CVintraResult:
    """Result from CVintra extraction"""
    cvintra: Optional[float] = None
    confidence: float = 0.0
    method: str = "unknown"  # 'regex', 'llm', 'hybrid'
    evidence: str = ""
    pmid: str = ""
    source_url: str = ""
    extracted_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        if not result.get("extracted_at"):
            result["extracted_at"] = datetime.now().isoformat()
        return result

    def is_valid(self) -> bool:
        """Check if result is valid and within acceptable range"""
        if self.cvintra is None:
            return False
        return 5 <= self.cvintra <= 100 and self.confidence > 0.0


class CVintraRegexExtractor:
    """Regex-based CVintra extraction - fast and reliable for standard formats"""

    # Comprehensive regex patterns for CVintra variations
    CV_PATTERNS = [
        # Exact intra-subject CV formats
        (r'cv\s*intra[-\s]?subject\s*[=:]\s*(\d+\.?\d*)\s*%', 0.95),
        (r'intra[-\s]?subject\s+cv\s*[=:]\s*(\d+\.?\d*)\s*%', 0.95),
        (r'intra[-\s]?subject\s+coefficient\s+of\s+variation\s*[=:]\s*(\d+\.?\d*)\s*%', 0.95),
        
        # CVintra without explicit "subject"
        (r'cv\s*intra\s*[=:]\s*(\d+\.?\d*)\s*%', 0.92),
        (r'cvintra\s*[=:]\s*(\d+\.?\d*)\s*%', 0.92),
        
        # Within-subject variations
        (r'within[-\s]?subject\s+cv\s*[=:]\s*(\d+\.?\d*)\s*%', 0.90),
        (r'within[-\s]?subject\s+coefficient\s+of\s+variation\s*[=:]\s*(\d+\.?\d*)\s*%', 0.90),
        
        # Intra-individual variations
        (r'intra[-\s]?individual\s+cv\s*[=:]\s*(\d+\.?\d*)\s*%', 0.88),
        (r'intra[-\s]?individual\s+variability\s*[=:]\s*(\d+\.?\d*)\s*%', 0.88),
        
        # CV patterns with specific mention of "intra"
        (r'cv\s*\(intra[-\s]?subject\)\s*[=:]\s*(\d+\.?\d*)\s*%', 0.93),
        (r'cv[\s\(]*intra\s*[=:]\s*(\d+\.?\d*)\s*%', 0.85),
        
        # Table-like formats
        (r'cvw\s*[=:]\s*(\d+\.?\d*)\s*%', 0.85),  # Common abbreviation for within-subject CV
        (r'cv_w\s*[=:]\s*(\d+\.?\d*)\s*%', 0.85),
        
        # Without % symbol (fallback)
        (r'cv\s*intra[-\s]?subject\s*[=:]\s*(\d+\.?\d*)(?:\s|$|[,.])', 0.70),
        (r'intra[-\s]?subject\s+cv\s*[=:]\s*(\d+\.?\d*)(?:\s|$|[,.])', 0.70),
    ]

    @staticmethod
    def extract_cvintra(text: str, pmid: str = "", url: str = "") -> List[CVintraResult]:
        """
        Extract CVintra values from text using regex patterns.
        Returns list of results sorted by confidence.
        """
        results = []

        if not text or not isinstance(text, str):
            return results

        # Preprocess text
        text_lower = text.lower()
        text_clean = text_lower.replace("\n", " ").replace("\t", " ")

        # Track extracted values to avoid duplicates
        extracted_values = set()

        for pattern, confidence in CVintraRegexExtractor.CV_PATTERNS:
            try:
                matches = re.finditer(pattern, text_clean, re.IGNORECASE)

                for match in matches:
                    try:
                        cv_value = float(match.group(1))

                        # Validate range
                        if not (5 <= cv_value <= 100):
                            continue

                        # Skip duplicates
                        if cv_value in extracted_values:
                            continue

                        extracted_values.add(cv_value)

                        # Extract evidence (context around match)
                        start = max(0, match.start() - 50)
                        end = min(len(text_clean), match.end() + 50)
                        evidence = text_clean[start : end].strip()

                        result = CVintraResult(
                            cvintra=cv_value,
                            confidence=confidence,
                            method="regex",
                            evidence=evidence,
                            pmid=pmid,
                            source_url=url,
                        )

                        if result.is_valid():
                            results.append(result)

                    except (ValueError, IndexError, AttributeError):
                        continue

            except re.error as e:
                logger.warning(f"Regex pattern error: {e}")
                continue

        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results


class CVintraLLMExtractor:
    """LLM-based CVintra extraction - for handling complex or non-standard formats"""

    SYSTEM_PROMPT = """You are a pharmacokinetics expert extracting structured data from scientific abstracts.

TASK:
Extract the intra-subject coefficient of variation (CVintra) from the text.

DEFINITION:
CVintra is the within-subject variability expressed as a percentage (%) in pharmacokinetic studies.

It may be written as:
- CVintra
- intra-subject CV
- within-subject CV
- intra-individual variability
- coefficient of variation (within subjects)

RULES:
1. Extract ONLY CVintra (not inter-subject variability)
2. Return value in percentage (%)
3. If multiple values exist, choose the most relevant PK parameter (Cmax or AUC)
4. Ignore values outside 5%–100%
5. If not found, return null
6. Do NOT hallucinate
7. Always provide exact evidence from text or null if not found

OUTPUT FORMAT (JSON ONLY):
{
    "cvintra": float | null,
    "confidence": 0-1,
    "evidence": "exact sentence from text or null"
}"""

    def __init__(self, llm_handler=None):
        """
        Initialize LLM extractor.
        If llm_handler is not provided, attempts to import from models.llm_handler
        """
        self.llm_handler = llm_handler
        
        if llm_handler is None:
            try:
                from backend.models.llm_handler import get_llm
                self.llm_handler = get_llm()
                logger.info("✓ LLM handler initialized")
            except Exception as e:
                logger.warning(f"⚠ Could not initialize LLM handler: {e}")
                self.llm_handler = None

    def extract_cvintra(
        self, text: str, pmid: str = "", url: str = "", abstract_only: bool = True
    ) -> Optional[CVintraResult]:
        """
        Extract CVintra using LLM.
        
        Args:
            text: Full text or abstract
            pmid: PubMed ID
            url: Source URL
            abstract_only: If True, limit to first 2000 characters (abstracts)
            
        Returns:
            CVintraResult or None if extraction fails
        """
        if self.llm_handler is None:
            logger.warning("LLM handler not available, falling back to regex extraction")
            return None

        try:
            # Limit text to abstract length to save tokens
            if abstract_only:
                text = text[:2000]

            # Create extraction prompt
            user_prompt = f"""Extract CVintra from this scientific abstract:

ABSTRACT:
{text}

Extract the CVintra value if present."""

            # Call LLM with JSON output
            response = self.llm_handler.generate_json(
                prompt=user_prompt, system_prompt=self.SYSTEM_PROMPT
            )

            if not response or "error" in response:
                logger.debug(f"LLM extraction inconclusive: {response}")
                return None

            # Parse response
            cvintra_value = response.get("cvintra")
            confidence = float(response.get("confidence", 0.0))
            evidence = response.get("evidence", "")

            # Validate
            if cvintra_value is None or not isinstance(cvintra_value, (int, float)):
                return None

            cvintra_value = float(cvintra_value)

            if not (5 <= cvintra_value <= 100):
                logger.debug(f"CVintra {cvintra_value} outside valid range (5-100%)")
                return None

            result = CVintraResult(
                cvintra=cvintra_value,
                confidence=confidence,
                method="llm",
                evidence=evidence,
                pmid=pmid,
                source_url=url,
            )

            if result.is_valid():
                logger.info(f"✓ LLM extracted CVintra: {cvintra_value}% (confidence: {confidence})")
                return result

            return None

        except Exception as e:
            logger.warning(f"LLM extraction error: {e}")
            return None


class CVintraValidator:
    """Validation and post-processing for CVintra results"""

    MIN_CV = 5.0
    MAX_CV = 100.0
    MIN_CONFIDENCE = 0.3

    @staticmethod
    def is_valid(result: CVintraResult) -> bool:
        """Check if CVintra result is valid"""
        if result.cvintra is None:
            return False

        is_in_range = CVintraValidator.MIN_CV <= result.cvintra <= CVintraValidator.MAX_CV
        has_confidence = result.confidence >= CVintraValidator.MIN_CONFIDENCE

        return is_in_range and has_confidence

    @staticmethod
    def aggregate_results(
        results: List[CVintraResult], method: str = "weighted_mean"
    ) -> Tuple[Optional[float], float, List[Dict[str, Any]]]:
        """
        Aggregate multiple CVintra results.
        
        Returns:
            (aggregated_value, aggregated_confidence, source_list)
        """
        if not results:
            return None, 0.0, []

        # Filter valid results
        valid_results = [r for r in results if CVintraValidator.is_valid(r)]

        if not valid_results:
            return None, 0.0, []

        if method == "weighted_mean":
            # Weighted average by confidence
            total_weight = sum(r.confidence for r in valid_results)
            if total_weight == 0:
                return None, 0.0, []

            weighted_sum = sum(
                r.cvintra * r.confidence for r in valid_results if r.cvintra is not None
            )
            aggregated_value = round(weighted_sum / total_weight, 2)
            aggregated_confidence = min(1.0, sum(r.confidence for r in valid_results) / len(valid_results))

        elif method == "median":
            values = sorted([r.cvintra for r in valid_results if r.cvintra is not None])
            n = len(values)
            if n == 0:
                return None, 0.0, []
            aggregated_value = values[n // 2]
            aggregated_confidence = sum(r.confidence for r in valid_results) / len(valid_results)

        else:  # mean
            values = [r.cvintra for r in valid_results if r.cvintra is not None]
            if not values:
                return None, 0.0, []
            aggregated_value = round(sum(values) / len(values), 2)
            aggregated_confidence = sum(r.confidence for r in valid_results) / len(valid_results)

        # Source tracking
        sources = [
            {
                "url": r.source_url,
                "method": r.method,
                "pmid": r.pmid,
                "value": r.cvintra,
                "confidence": r.confidence,
            }
            for r in valid_results
        ]

        return aggregated_value, aggregated_confidence, sources


class CVintraExtractor:
    """Main extraction pipeline combining regex + LLM"""

    def __init__(self, llm_handler=None, use_llm_fallback: bool = True):
        """
        Initialize CVintra extractor.
        
        Args:
            llm_handler: Optional LLM handler for advanced extraction
            use_llm_fallback: If True, use LLM for low-confidence regex results
        """
        self.regex_extractor = CVintraRegexExtractor()
        self.llm_extractor = CVintraLLMExtractor(llm_handler=llm_handler) if use_llm_fallback else None
        self.validator = CVintraValidator()

    def extract(
        self, text: str, pmid: str = "", url: str = "", use_llm: bool = True
    ) -> List[CVintraResult]:
        """
        Extract CVintra using hybrid approach.
        
        1. First try regex (fast, reliable)
        2. If low confidence or no match, try LLM (slow, better understanding)
        
        Returns:
            List of CVintraResult sorted by confidence
        """
        results = []

        # Step 1: Regex extraction
        regex_results = self.regex_extractor.extract_cvintra(text, pmid=pmid, url=url)
        results.extend(regex_results)

        # Step 2: LLM fallback if needed
        if use_llm and self.llm_extractor and self.llm_extractor.llm_handler:
            # Try LLM if:
            # 1. No regex results found, OR
            # 2. Best regex result has low confidence (<0.8)
            if not regex_results or (regex_results and regex_results[0].confidence < 0.8):
                try:
                    llm_result = self.llm_extractor.extract_cvintra(text, pmid=pmid, url=url)
                    if llm_result and llm_result not in results:
                        results.append(llm_result)
                except Exception as e:
                    logger.warning(f"LLM extraction failed: {e}")

        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results

    def extract_from_articles(
        self, articles: List[Dict[str, str]], use_llm: bool = True
    ) -> Tuple[Optional[float], float, List[Dict[str, Any]], List[CVintraResult]]:
        """
        Extract CVintra from multiple articles.
        
        Args:
            articles: List of article dicts with keys: 'pmid', 'title', 'abstract', 'url'
            use_llm: Whether to use LLM fallback
            
        Returns:
            (aggregated_cvintra, confidence, sources, all_results)
        """
        all_results = []

        for article in articles:
            pmid = article.get("pmid", "")
            url = article.get("url", "")
            
            # Combine title and abstract
            text = f"{article.get('title', '')} {article.get('abstract', '')}"

            if not text.strip():
                continue

            # Extract CVintra
            results = self.extract(text, pmid=pmid, url=url, use_llm=use_llm)
            all_results.extend(results)

        # Aggregate results
        agg_value, agg_confidence, sources = self.validator.aggregate_results(all_results)

        logger.info(
            f"✓ Extracted CVintra from {len(articles)} articles: "
            f"value={agg_value}%, items={len(all_results)}"
        )

        return agg_value, agg_confidence, sources, all_results
