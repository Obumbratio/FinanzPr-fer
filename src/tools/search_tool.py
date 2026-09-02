import logging
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from src.config import settings

logger = logging.getLogger(__name__)

class FinancialSearchTool:
    """
    Herramienta de búsqueda en vivo para contexto financiero y noticias de mercado.
    Habilita las runtime calls a Tavily requeridas para el bono de $3,000 USD.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TAVILY_API_KEY
        self._client: Optional[TavilyClient] = None
        
        if self.api_key and self.api_key != "tu_clave_aqui":
            try:
                self._client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Error inicializando TavilyClient: {e}")

    def is_configured(self) -> bool:
        return self._client is not None

    def search_market_news(
        self, 
        query: str, 
        max_results: int = 5,
        include_domains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta una búsqueda de noticias financieras optimizada para agentes LLM.
        
        Dominios por defecto: Fuentes confiables de finanzas y mercados.
        """
        if not self.is_configured():
            return [{
                "title": "Configuración incompleta",
                "url": "",
                "content": "TAVILY_API_KEY no está configurada o es inválida en el entorno.",
                "score": 0.0
            }]

        default_domains = [
            "bloomberg.com",
            "reuters.com",
            "wsj.com",
            "cnbc.com",
            "marketwatch.com",
            "sec.gov",
            "finance.yahoo.com"
        ]
        domains = include_domains or default_domains

        try:
            # Consulta a la API de Tavily con parámetros de búsqueda profunda
            response = self._client.search(
                query=f"{query} financial news",
                search_depth="advanced",
                max_results=max_results,
                include_domains=domains
            )
            
            clean_results = []
            for item in response.get("results", []):
                clean_results.append({
                    "title": item.get("title", "Sin título"),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0.0),
                    "published_date": item.get("published_date", "N/A")
                })
                
            return clean_results

        except Exception as e:
            logger.error(f"Fallo durante la búsqueda con Tavily: {e}")
            return [{
                "title": "Error de ejecución",
                "url": "",
                "content": f"Ocurrió un error al contactar la API de Tavily: {str(e)}",
                "score": 0.0
            }]
