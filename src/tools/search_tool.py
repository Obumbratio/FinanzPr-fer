import logging
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from src.config import settings

logger = logging.getLogger(__name__)

class FinancialSearchTool:
    """
    Herramienta agéntica de búsqueda web y consenso de analistas en tiempo real.
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
        max_results: int = 4,
        include_domains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Busca noticias de mercado y catalizadores recientes."""
        if not self.is_configured():
            return [{
                "title": "Fallback Context",
                "url": "",
                "content": "Tavily API no disponible. Operando bajo contexto interno estructurado.",
                "score": 0.0
            }]

        default_domains = [
            "bloomberg.com", "reuters.com", "wsj.com", 
            "cnbc.com", "marketwatch.com", "sec.gov", "finance.yahoo.com"
        ]
        domains = include_domains or default_domains

        try:
            response = self._client.search(
                query=f"{query} market financial news catalysts",
                search_depth="advanced",
                max_results=max_results,
                include_domains=domains
            )
            return [
                {
                    "title": item.get("title", "Sin título"),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "published_date": item.get("published_date", "N/A")
                }
                for item in response.get("results", [])
            ]
        except Exception as e:
            logger.warning(f"Fallback activado en search_market_news: {e}")
            return [{"error": f"Fallo temporal de conexión con Tavily: {str(e)}"}]

    def get_analyst_consensus(self, ticker: str) -> Dict[str, Any]:
        """
        Extrae el consenso de analistas de Wall Street, ratings y precios objetivo
        recuperados en tiempo real (TipRanks, FactSet, analistas principales).
        """
        ticker = ticker.upper().replace("$", "")
        if not self.is_configured():
            return {
                "ticker": ticker,
                "consensus_status": "DATA_UNAVAILABLE",
                "message": "Tavily no configurado."
            }

        try:
            query = f"{ticker} stock price target analyst consensus ratings Wall Street TipRanks"
            response = self._client.search(
                query=query,
                search_depth="advanced",
                max_results=3,
                include_domains=["tipranks.com", "marketwatch.com", "finance.yahoo.com", "cnbc.com"]
            )
            
            snippets = [r.get("content", "") for r in response.get("results", [])]
            return {
                "ticker": ticker,
                "source": "Wall Street Analyst Aggregation (via Tavily)",
                "snippets": snippets,
                "status": "SUCCESS"
            }
        except Exception as e:
            logger.warning(f"Error consultando consenso de analistas para {ticker}: {e}")
            return {
                "ticker": ticker,
                "status": "FALLBACK",
                "message": f"No se pudo consultar el consenso en vivo: {str(e)}"
            }
