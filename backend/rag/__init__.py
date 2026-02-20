"""
RAG (Retrieval Augmented Generation) Pipeline для BE исследований
Использует LangChain, FAISS и HuggingFace embeddings
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Версия модуля
__version__ = '1.0.0'
__all__ = [
    'DocumentLoader',
    'VectorStore',
    'RAGPipeline',
    'build_knowledge_base'
]

# Ленивая загрузка компонентов для оптимизации производительности
def __getattr__(name: str):
    """Динамическая загрузка компонентов RAG"""
    if name == 'DocumentLoader':
        from .document_loader import DocumentLoader
        return DocumentLoader
    elif name == 'VectorStore':
        from .vector_store import VectorStore
        return VectorStore
    elif name == 'RAGPipeline':
        from .rag_pipeline import RAGPipeline
        return RAGPipeline
    elif name == 'build_knowledge_base':
        from .build_index import build_knowledge_base
        return build_knowledge_base
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
