"""
Intelligent Drug Lookup with Live Data Mode
============================================
Features:
- Live Data Mode: Auto-fallback to PubMed if drug not in local DB
- Hugging Face QA: Answer questions about drugs from scientific data
- Semantic Search: Vector embeddings for better context retrieval
- Comprehensive Logging: Production-ready logging
- Status Tracking: Track processing steps for UI

This module is the "WOW-FACTOR" - seamless integration of cloud + local data
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import requests

# Configure logging with timestamps and levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class StatusTracker:
    """Track processing steps for frontend UI"""
    def __init__(self):
        self.steps = []
        self.current_step = None
    
    def start_step(self, step_name: str, description: str = ""):
        """Start tracking a step"""
        self.current_step = {
            "name": step_name,
            "description": description,
            "start_time": datetime.now().isoformat(),
            "status": "in-progress"
        }
        self.steps.append(self.current_step)
        logger.info(f"📍 Step: {step_name} - {description}")
        return self.current_step
    
    def end_step(self, status: str = "completed", message: str = ""):
        """End current step"""
        if self.current_step:
            self.current_step["status"] = status
            self.current_step["end_time"] = datetime.now().isoformat()
            if message:
                self.current_step["message"] = message
            logger.info(f"✓ Step completed: {self.current_step['name']} ({status})")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status for UI"""
        return {
            "steps": self.steps,
            "current": self.current_step,
            "progress": f"{len([s for s in self.steps if s['status'] == 'completed'])}/{len(self.steps)}"
        }


class LiveDataFetcher:
    """
    Live Data Mode: Intelligently fetch drug info from multiple sources
    Local DB → PubMed → DrugBank (fallback chain)
    """
    
    def __init__(self, status_tracker: Optional[StatusTracker] = None):
        self.status = status_tracker or StatusTracker()
        self.pubmed_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.pubmed_api_key = os.getenv("NCBI_API_KEY", "")
    
    def get_drug_info(self, inn: str, use_local_first: bool = True) -> Dict[str, Any]:
        """
        Intelligent drug lookup:
        1. Check local database (Решение №85)
        2. If not found → PubMed search (Live Data)
        3. If still missing → DrugBank fallback
        
        Returns: Unified drug info dict
        """
        logger.info(f"🔍 Starting intelligent lookup for: {inn}")
        self.status.start_step("local_search", f"Checking local database for {inn}")
        
        result = {
            "inn": inn,
            "sources_used": [],
            "data": {},
            "confidence": 0.0
        }
        
        # Step 1: Try local database (Решение №85)
        try:
            from cv_database import get_typical_cv
            cv_value = get_typical_cv(inn)
            if cv_value:
                logger.info(f"✓ Found in local DB: CVintra={cv_value}%")
                result["data"]["cvintra"] = cv_value
                result["sources_used"].append("local_database")
                result["confidence"] = 0.85
                self.status.end_step("completed", f"Found CVintra={cv_value}% in local DB")
                return result
        except Exception as e:
            logger.debug(f"Local lookup error: {e}")
        
        self.status.end_step("completed", "Drug not in local DB, proceeding to live data")
        
        # Step 2: Live Data from PubMed (THE WOW FACTOR!)
        logger.info(f"🌍 Fetching live data from PubMed for {inn}...")
        self.status.start_step("pubmed_search", f"Searching PubMed for {inn}")
        
        try:
            from scrapers.pubmed_scraper import PubMedScraper
            scraper = PubMedScraper()
            pubmed_data = scraper.get_drug_pk_data(inn)
            
            if pubmed_data.get("status") == "success":
                result["data"]["pubmed"] = pubmed_data
                result["sources_used"].append("pubmed_live")
                result["confidence"] = max(result["confidence"], pubmed_data.get("cvintra_confidence", 0.5))
                logger.info(f"✓ PubMed search successful: {pubmed_data.get('n_articles', 0)} articles")
                self.status.end_step("completed", f"Found {pubmed_data.get('n_articles')} PubMed articles")
                return result
        except Exception as e:
            logger.warning(f"PubMed fetch error: {e}")
            self.status.end_step("failed", str(e))
        
        # Step 3: Fallback to DrugBank
        logger.info(f"🔄 Fallback to DrugBank for {inn}...")
        self.status.start_step("drugbank_search", f"Searching DrugBank for {inn}")
        
        try:
            from scrapers.drugbank_scraper import DrugBankScraper
            scraper = DrugBankScraper()
            db_data = scraper.get_drug_info(inn)
            
            if db_data.get("status") != "error":
                result["data"]["drugbank"] = db_data
                result["sources_used"].append("drugbank")
                result["confidence"] = max(result["confidence"], 0.6)
                logger.info(f"✓ DrugBank data retrieved")
                self.status.end_step("completed", "DrugBank data retrieved")
                return result
        except Exception as e:
            logger.warning(f"DrugBank fetch error: {e}")
            self.status.end_step("failed", str(e))
        
        # No data found
        logger.warning(f"⚠️ No data found for {inn} from any source")
        self.status.start_step("fallback", "Using default values")
        result["sources_used"].append("default_fallback")
        result["confidence"] = 0.0
        self.status.end_step("completed", "Using default fallback values")
        
        return result


class HuggingFaceQA:
    """
    Question-Answering powered by Hugging Face
    Ask questions about drug information
    """
    
    def __init__(self):
        self.qa_pipeline = None
        self._initialize()
    
    def _initialize(self):
        """Lazy load the QA pipeline"""
        try:
            from transformers import pipeline
            logger.info("🚀 Loading Hugging Face QA pipeline...")
            self.qa_pipeline = pipeline(
                "question-answering",
                model="distilbert-base-cased-distilled-squad"
            )
            logger.info("✓ QA pipeline loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not load QA pipeline: {e}")
            logger.info("   QA feature will be disabled")
            self.qa_pipeline = None
    
    def ask_question(self, context: str, question: str) -> Optional[Dict[str, Any]]:
        """
        Ask a question about the context
        
        Returns: {"answer": str, "score": float, "start": int, "end": int}
        """
        if not self.qa_pipeline:
            logger.warning("QA pipeline not available")
            return None
        
        if not context or not question:
            logger.warning("Empty context or question")
            return None
        
        try:
            logger.info(f"❓ QA: {question}")
            
            # Limit context to 512 tokens for model
            context_limited = context[:1024]
            
            result = self.qa_pipeline(
                question=question,
                context=context_limited,
                top_k=1
            )
            
            if result:
                ans = result[0] if isinstance(result, list) else result
                logger.info(f"✓ Answer: {ans.get('answer', 'N/A')[:100]}... (score: {ans.get('score', 0):.2f})")
                return ans
        except Exception as e:
            logger.error(f"QA error: {e}")
        
        return None
    
    def batch_questions(self, context: str, questions: List[str]) -> List[Dict[str, Any]]:
        """Ask multiple questions"""
        results = []
        for q in questions:
            ans = self.ask_question(context, q)
            if ans:
                results.append({
                    "question": q,
                    "answer": ans.get("answer"),
                    "score": ans.get("score")
                })
        return results


class SemanticSearchRAG:
    """
    Semantic Search for RAG
    Uses embeddings instead of keyword matching
    """
    
    def __init__(self):
        self.model = None
        self.embeddings_cache = {}
        self._initialize()
    
    def _initialize(self):
        """Load semantic search model"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("🚀 Loading semantic search model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✓ Semantic search model loaded")
        except Exception as e:
            logger.warning(f"⚠️ Could not load semantic model: {e}")
            self.model = None
    
    def encode_text(self, text: str) -> Optional[List[float]]:
        """Convert text to embedding vector"""
        if not self.model:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Encoding error: {e}")
            return None
    
    def semantic_search(self, query: str, documents: List[Dict[str, str]], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Semantic search across documents
        
        Args:
            query: Search query
            documents: List of {"title": str, "text": str, "source": str}
            top_k: Number of results
            
        Returns: Ranked documents by semantic similarity
        """
        if not self.model or not documents:
            logger.warning("Semantic search not available or no documents")
            return []
        
        try:
            logger.info(f"🔍 Semantic search: '{query}'")
            
            # Encode query
            query_embedding = self.encode_text(query)
            if not query_embedding:
                return []
            
            # Score documents
            import numpy as np
            scores = []
            
            for doc in documents:
                doc_text = f"{doc.get('title', '')} {doc.get('text', '')}"
                doc_embedding = self.encode_text(doc_text)
                
                if doc_embedding:
                    # Cosine similarity
                    similarity = np.dot(query_embedding, doc_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding) + 1e-8
                    )
                    scores.append((doc, float(similarity)))
            
            # Sort by score
            scores.sort(key=lambda x: x[1], reverse=True)
            
            results = [
                {
                    "document": doc,
                    "score": score
                }
                for doc, score in scores[:top_k]
            ]
            
            logger.info(f"✓ Found {len(results)} semantically relevant documents")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []


class IntelligentDrugAnalyzer:
    """
    Main orchestrator combining all WOW features
    """
    
    def __init__(self):
        self.status = StatusTracker()
        self.fetcher = LiveDataFetcher(self.status)
        self.qa = HuggingFaceQA()
        self.rag = SemanticSearchRAG()
        logger.info("🎯 Intelligent Drug Analyzer initialized")
    
    def analyze_drug(self, inn: str, questions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Full drug analysis with all WOW features
        
        Returns: Complete analysis with data, QA, semantic insights
        """
        logger.info("=" * 60)
        logger.info(f"📊 ANALYZING DRUG: {inn}")
        logger.info("=" * 60)
        
        self.status.start_step("initialization", f"Starting analysis for {inn}")
        
        analysis = {
            "inn": inn,
            "timestamp": datetime.now().isoformat(),
            "drug_data": {},
            "qa_results": [],
            "semantic_insights": [],
            "status_log": [],
            "processing_time": 0
        }
        
        import time
        start_time = time.time()
        
        self.status.end_step("completed", "Initialization complete")
        
        # Step 1: Live Data Fetch
        logger.info("\n" + " " * 20 + "🌍 LIVE DATA MODE")
        analysis["drug_data"] = self.fetcher.get_drug_info(inn)
        
        # Step 2: QA (if context available)
        if questions and analysis["drug_data"].get("data"):
            logger.info("\n" + " " * 20 + "❓ QUESTION ANSWERING")
            self.status.start_step("qa", f"Processing {len(questions)} questions")
            
            context = json.dumps(analysis["drug_data"], ensure_ascii=False)[:2000]
            analysis["qa_results"] = self.qa.batch_questions(context, questions)
            
            self.status.end_step("completed", f"Answered {len(analysis['qa_results'])} questions")
        
        # Step 3: Semantic Search (if articles available)
        logger.info("\n" + " " * 20 + "🔍 SEMANTIC SEARCH")
        self.status.start_step("semantic_search", "Performing semantic analysis")
        
        pubmed_data = analysis["drug_data"].get("data", {}).get("pubmed", {})
        articles = pubmed_data.get("articles", [])
        
        if articles:
            documents = [
                {
                    "title": a.get("title", ""),
                    "text": a.get("abstract", "") or a.get("title", ""),
                    "source": f"PubMed:{a.get('pmid')}"
                }
                for a in articles[:10]
            ]
            
            # Search for key terms
            search_queries = [
                f"{inn} pharmacokinetics",
                f"{inn} CVintra variability",
                f"{inn} bioavailability"
            ]
            
            for query in search_queries:
                results = self.rag.semantic_search(query, documents, top_k=2)
                if results:
                    analysis["semantic_insights"].append({
                        "query": query,
                        "results": results
                    })
        
        self.status.end_step("completed", f"Found {len(analysis['semantic_insights'])} insights")
        
        # Calculate processing time
        analysis["processing_time"] = time.time() - start_time
        analysis["status_log"] = self.status.get_status()
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ ANALYSIS COMPLETE")
        logger.info(f"   Time: {analysis['processing_time']:.2f}s")
        logger.info(f"   Sources: {', '.join(analysis['drug_data'].get('sources_used', []))}")
        logger.info(f"   Confidence: {analysis['drug_data'].get('confidence', 0):.2%}")
        logger.info("=" * 60 + "\n")
        
        return analysis


if __name__ == "__main__":
    # Demo
    analyzer = IntelligentDrugAnalyzer()
    
    questions = [
        "What is the CVintra for aspirin?",
        "Is aspirin bioequivalent in fasted state?",
        "What are the main pharmacokinetic parameters?"
    ]
    
    result = analyzer.analyze_drug("aspirin", questions=questions)
    
    print("\n" + "=" * 60)
    print("📋 ANALYSIS RESULT")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
