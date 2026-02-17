import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    
    # LLM settings
    HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    
    # Alternative models
    MODELS = {
        "mistral": "mistralai/Mistral-7B-Instruct-v0.2",
        "llama": "meta-llama/Llama-2-7b-chat-hf",
        "zephyr": "HuggingFaceH4/zephyr-7b-beta",
        "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0"  # для слабых ПК
    }
    
    # RAG settings
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "vectorstore_index")
    KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "knowledge_base")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", 5))
    
    # Scraping settings
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    PUBMED_EMAIL = os.getenv("PUBMED_EMAIL", "your.email@example.com")
    
    # Output settings
    OUTPUT_DIR = "outputs"
    SUPPORTED_FORMATS = ["docx", "json", "markdown"]
    
    # Performance
    USE_GPU = torch.cuda.is_available() if 'torch' in dir() else False
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
