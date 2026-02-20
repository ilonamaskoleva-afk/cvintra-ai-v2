"""
Vector Store для RAG системы
Использует FAISS для хранения и поиска по векторам embeddings
"""

import os
import logging
from typing import List, Dict, Tuple, Optional

try:
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import FAISS
except ImportError:
    raise ImportError("LangChain не установлен. Установите: pip install langchain")

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Векторное хранилище для RAG
    
    Поддерживаемые модели embeddings:
    - all-MiniLM-L6-v2: 384 dim, быстрая, хорошее качество (default)
    - all-mpnet-base-v2: 768 dim, медленнее, лучше качество
    - multilingual-e5-large: 1024 dim, русский + английский (рекомендуется для многоязычных текстов)
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        """
        Инициализация векторного хранилища
        
        Args:
            model_name: Имя модели embeddings из HuggingFace
            device: "cpu" или "cuda" для GPU
        """
        logger.info(f"Инициализация VectorStore с моделью: {model_name}")
        logger.info(f"Устройство: {device}")
        
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )
            self.vectorstore = None
            self.index_path = "vectorstore_index"
            logger.info("✓ VectorStore инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации: {str(e)}")
            raise
    
    def create_vectorstore(self, documents: List) -> bool:
        """
        Создание векторного хранилища из документов
        
        Args:
            documents: Список документов LangChain
        
        Returns:
            bool: True если успешно
        """
        logger.info(f"Создаю векторное хранилище из {len(documents)} документов...")
        
        try:
            self.vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            logger.info(f"✓ Векторное хранилище создано")
            return True
        except Exception as e:
            logger.error(f"Ошибка создания хранилища: {str(e)}")
            return False
    
    def save(self, path: Optional[str] = None) -> bool:
        """
        Сохранение векторного хранилища на диск
        
        Args:
            path: Путь сохранения (используется default если не указан)
        
        Returns:
            bool: True если успешно
        """
        if self.vectorstore is None:
            logger.error("Векторное хранилище не создано!")
            return False
        
        if path is None:
            path = self.index_path
        
        logger.info(f"Сохраняю хранилище в '{path}'...")
        
        try:
            self.vectorstore.save_local(path)
            logger.info(f"✓ Хранилище сохранено в '{path}'")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}")
            return False
    
    def load(self, path: Optional[str] = None) -> bool:
        """
        Загрузка векторного хранилища с диска
        
        Args:
            path: Путь загрузки (используется default если не указан)
        
        Returns:
            bool: True если успешно загружено
        """
        if path is None:
            path = self.index_path
        
        if not os.path.exists(path):
            logger.warning(f"Индекс не найден: {path}")
            return False
        
        logger.info(f"Загружаю хранилище из '{path}'...")
        
        try:
            self.vectorstore = FAISS.load_local(
                path,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"✓ Хранилище загружено")
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки: {str(e)}")
            return False
    
    def search(
        self,
        query: str,
        k: int = 3,
        score_threshold: Optional[float] = None
    ) -> List[Tuple]:
        """
        Поиск релевантных документов
        
        Args:
            query: Поисковый запрос
            k: Количество результатов
            score_threshold: Минимальный порог релевантности (0-1)
        
        Returns:
            List of (Document, score) tuples
        """
        if self.vectorstore is None:
            logger.error("Векторное хранилище не загружено!")
            return []
        
        logger.info(f"Поиск: '{query}' (top-{k})")
        
        try:
            # Поиск с оценкой релевантности
            results = self.vectorstore.similarity_search_with_score(
                query,
                k=k * 2  # Получаем больше, потом фильтруем
            )
            
            # Фильтрование по threshold если указан
            if score_threshold is not None:
                results = [
                    (doc, score) for doc, score in results
                    if (1 - score) >= score_threshold  # FAISS возвращает расстояние, конвертируем в similarity
                ]
                results = results[:k]
            else:
                results = results[:k]
            
            logger.info(f"✓ Найдено {len(results)} результатов")
            
            # Логирование результатов
            for i, (doc, score) in enumerate(results):
                source = doc.metadata.get('source', 'N/A')
                doc_type = doc.metadata.get('type', 'general')
                logger.debug(f"  {i+1}. Score: {(1-score):.3f} | Type: {doc_type} | Source: {source}")
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {str(e)}")
            return []
    
    def is_loaded(self) -> bool:
        """Проверка загружено ли хранилище"""
        return self.vectorstore is not None
