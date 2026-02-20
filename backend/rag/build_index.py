"""
Build Knowledge Base Index для RAG системы
Создает и сохраняет FAISS индекс из документов knowledge_base
"""

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def build_knowledge_base(
    knowledge_base_path: str = "knowledge_base",
    output_path: str = "vectorstore_index",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> bool:
    """
    Построение индекса знаниевой базы
    
    Args:
        knowledge_base_path: Путь к папке с документами
        output_path: Путь сохранения индекса
        chunk_size: Размер куска текста
        chunk_overlap: Перекрытие между кусками
        model_name: Модель embeddings
    
    Returns:
        bool: True если успешно, False если ошибка
    """
    try:
        from document_loader import DocumentLoader
        from vector_store import VectorStore
    except ImportError:
        logger.error("LangChain не установлен. Установите: pip install langchain")
        return False
    
    logger.info("=" * 80)
    logger.info("ПОСТРОЕНИЕ ИНДЕКСА ЗНАНИЕВОЙ БАЗЫ")
    logger.info("=" * 80)
    
    # Шаг 1: Загрузка документов
    logger.info("\n[1/3] Загрузка документов...")
    loader = DocumentLoader(
        docs_path=knowledge_base_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    chunks = loader.load_documents()
    
    if not chunks:
        logger.error("✗ Документы не загружены. Проверьте папку knowledge_base")
        return False
    
    logger.info(f"✓ Загружено и обработано {len(chunks)} чанков")
    
    # Шаг 2: Векторизация и создание индекса
    logger.info("\n[2/3] Создание векторного индекса...")
    vectorstore = VectorStore(model_name=model_name)
    
    try:
        vectorstore.create_vectorstore(chunks)
        logger.info("✓ Индекс создан")
    except Exception as e:
        logger.error(f"✗ Ошибка создания индекса: {str(e)}")
        return False
    
    # Шаг 3: Сохранение индекса
    logger.info("\n[3/3] Сохранение индекса на диск...")
    try:
        vectorstore.save(output_path)
        logger.info(f"✓ Индекс сохранен в '{output_path}'")
    except Exception as e:
        logger.error(f"✗ Ошибка сохранения индекса: {str(e)}")
        return False
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ ИНДЕКС УСПЕШНО ПОСТРОЕН")
    logger.info("=" * 80)
    logger.info(f"\nИнформация:")
    logger.info(f"  - Документов загружено: {len(chunks)}")
    logger.info(f"  - Модель embeddings: {model_name}")
    logger.info(f"  - Сохранено в: {Path(output_path).absolute()}")
    logger.info("")
    
    return True


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Параметры (можно переопределить из командной строки)
    kb_path = "knowledge_base"
    output = "vectorstore_index"
    model = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Запуск построения
    success = build_knowledge_base(
        knowledge_base_path=kb_path,
        output_path=output,
        model_name=model
    )
    
    sys.exit(0 if success else 1)
