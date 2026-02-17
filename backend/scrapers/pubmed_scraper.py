import requests
from bs4 import BeautifulSoup
from Bio import Entrez
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PubMedScraper:
    def __init__(self, email: str = "your.email@example.com"):
        """
        Инициализация PubMed scraper
        email нужен для Entrez API (требование NCBI)
        """
        Entrez.email = email
        self.base_url = "https://pubmed.ncbi.nlm.nih.gov"
    
    def search_drug(self, inn: str, keywords: list = None) -> list:
        """
        Поиск статей о препарате в PubMed
        
        Args:
            inn: International Nonproprietary Name препарата
            keywords: дополнительные ключевые слова (pharmacokinetics, bioequivalence, etc.)
        
        Returns:
            list: список PMID статей
        """
        if keywords is None:
            keywords = ["pharmacokinetics", "bioequivalence", "Cmax", "AUC"]
        
        query = f"{inn} AND ({' OR '.join(keywords)})"
        
        try:
            logger.info(f"Поиск в PubMed: {query}")
            
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=20,  # максимум 20 статей
                sort="relevance"
            )
            
            record = Entrez.read(handle)
            handle.close()
            
            pmids = record["IdList"]
            logger.info(f"Найдено {len(pmids)} статей")
            
            return pmids
            
        except Exception as e:
            logger.error(f"Ошибка поиска в PubMed: {e}")
            return []
    
    def fetch_article_details(self, pmid: str) -> dict:
        """
        Получить детали статьи по PMID
        """
        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=pmid,
                rettype="abstract",
                retmode="xml"
            )
            
            record = Entrez.read(handle)
            handle.close()
            
            article = record['PubmedArticle'][0]
            medline = article['MedlineCitation']
            
            title = medline['Article']['ArticleTitle']
            abstract = ""
            
            if 'Abstract' in medline['Article']:
                abstract_texts = medline['Article']['Abstract']['AbstractText']
                abstract = ' '.join([str(text) for text in abstract_texts])
            
            authors = []
            if 'AuthorList' in medline['Article']:
                for author in medline['Article']['AuthorList']:
                    if 'LastName' in author and 'Initials' in author:
                        authors.append(f"{author['LastName']} {author['Initials']}")
            
            year = ""
            if 'PubDate' in medline['Article']['Journal']['JournalIssue']:
                pub_date = medline['Article']['Journal']['JournalIssue']['PubDate']
                year = pub_date.get('Year', '')
            
            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "year": year,
                "url": f"{self.base_url}/{pmid}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статьи {pmid}: {e}")
            return {}
    
    def extract_pk_parameters(self, articles: list) -> dict:
        """
        Извлечение PK параметров из абстрактов статей
        (простой текстовый поиск, в реальности нужен LLM)
        """
        pk_data = {
            "cmax": [],
            "auc": [],
            "tmax": [],
            "t_half": [],
            "cvintra": [],
            "sources": []
        }
        
        for article in articles:
            abstract = article.get("abstract", "").lower()
            
            # Простой парсинг (можно улучшить с regex или LLM)
            if "cmax" in abstract:
                pk_data["sources"].append(article["url"])
            
            # В реальности здесь нужен LLM для точного извлечения
        
        return pk_data
    
    def get_drug_pk_data(self, inn: str) -> dict:
        """
        Полный цикл: поиск + извлечение PK параметров
        """
        pmids = self.search_drug(inn)
        
        if not pmids:
            return {"error": "No articles found"}
        
        articles = []
        for pmid in pmids[:10]:  # Берем топ 10
            article = self.fetch_article_details(pmid)
            if article:
                articles.append(article)
            time.sleep(0.5)  # Rate limiting
        
        pk_data = self.extract_pk_parameters(articles)
        pk_data["articles"] = articles
        
        return pk_data
