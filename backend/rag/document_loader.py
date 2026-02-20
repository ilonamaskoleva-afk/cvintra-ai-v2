"""
Document Loader для RAG система
Загружает и разбивает документы из knowledge base на чанки
"""

import os
import logging
from typing import List, Optional
from pathlib import Path

try:
    from langchain.document_loaders import TextLoader, DirectoryLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    raise ImportError("LangChain не установлен. Установите: pip install langchain")

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Загрузчик документов для knowledge base
    
    Параметры:
        docs_path (str): Путь к папке с документами (default: "knowledge_base")
        chunk_size (int): Размер одного куска в символах (default: 1000)
        chunk_overlap (int): Перекрытие между кусками (default: 200)
    """
    
    def __init__(
        self, 
        docs_path: str = "knowledge_base",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """Инициализация загрузчика документов"""
        self.docs_path = docs_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
        logger.info(
            f"DocumentLoader инициализирован: "
            f"path={docs_path}, chunk_size={chunk_size}, overlap={chunk_overlap}"
        )
    
    def load_documents(self) -> List:
        """
        Загрузка всех документов из знаниевой базы
        
        Returns:
            List: Список документов разбитых на чанки
        """
        logger.info(f"Загружаю документы из '{self.docs_path}'...")
        
        # Проверяем наличие папки
        if not os.path.exists(self.docs_path):
            logger.warning(f"Папка не найдена: {self.docs_path}")
            return []
        
        try:
            # Загрузка всех .txt файлов рекурсивно
            loader = DirectoryLoader(
                self.docs_path,
                glob="**/*.txt",
                loader_cls=TextLoader,
                loader_kwargs={'encoding': 'utf-8'},
                recursive=True
            )
            
            documents = loader.load()
            logger.info(f"✓ Загружено {len(documents)} документов")
            
            if not documents:
                logger.warning("Документы не найдены в папке!")
                return []
            
            # Разбиение на чанки
            logger.info(f"Разбиваю документы на чанки (размер={self.chunk_size})...")
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"✓ Создано {len(chunks)} чанков")
            
            # Добавляем метаданные
            chunks = self.add_metadata(chunks)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке документов: {str(e)}")
            raise
    
    def add_metadata(self, chunks: List) -> List:
        """
        Добавление метаданных к чанкам документов
        
        Args:
            chunks (List): Список чанков
        
        Returns:
            List: Чанки с добавленными метаданными
        """
        for i, chunk in enumerate(chunks):
            # Определяем тип документа по имени файла
            source = chunk.metadata.get('source', '')
            
            # Определяем категорию
            if 'decision_85' in source.lower():
                chunk.metadata['type'] = 'regulation_russia'
                chunk.metadata['authority'] = 'EEC'
            elif 'ema' in source:
                chunk.metadata['type'] = 'regulation_international'
                chunk.metadata['authority'] = 'EMA'
            elif 'fda' in source:
                chunk.metadata['type'] = 'regulation_international'
                chunk.metadata['authority'] = 'FDA'
            elif 'protocol' in source:
                chunk.metadata['type'] = 'example_protocol'
            else:
                chunk.metadata['type'] = 'general'
        
        return chunks
```

---

## 🔢 **Шаг 2: Векторизация (Embeddings)**

### **2.1 Что такое Embeddings**
```
Текст: "При CV > 50% требуется 4-way replicate дизайн"
       ↓ (Embedding model)
Vector: [0.23, -0.45, 0.89, ..., 0.12]  # 384 числа
