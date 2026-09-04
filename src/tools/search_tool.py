import logging
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from src.config import settings

logger = logging.getLogger(__name__)

class FinancialSearchTool:
    """
    Herramienta agéntica de búsqueda web y consenso de analistas en tiempo real.
    Implementa protocolo Fail-Closed: nunca simula datos ni genera titulares ficticios.
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
    ) -> Dict[str, Any]:
        """
        Busca noticias de mercado y catalizadores recientes vía Tavily.
        Protocolo Fail-Closed: ante fallas o falta de API key, reporta UNAVAILABLE.
        """
        if not self.is_configured():
            return {
                "status": "UNAVAILABLE",
                "reason": "TAVILY_API_ERROR",
                "message": "Tavily API no configurada en el entorno.",
                "results": []
            }

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
            raw_results = response.get("results", [])
            clean_items = [
                {
                    "title": item.get("title", "Sin título"),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "published_date": item.get("published_date", "N/A")
                }
                for item in raw_results
            ]
            return {
                "status": "SUCCESS",
                "results": clean_items,
                "count": len(clean_items)
            }
        except Exception as e:
            logger.warning(f"Error en search_market_news: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": "TAVILY_API_ERROR",
                "message": f"Fallo en la consulta a Tavily: {str(e)}",
                "results": []
            }

    def get_analyst_consensus(self, ticker: str) -> Dict[str, Any]:
        """
        Extrae fragmentos fácticos del consenso de analistas de Wall Street y precios objetivo.
        Protocolo Fail-Closed: si no hay datos o falla Tavily, reporta status UNAVAILABLE.
        """
        ticker = ticker.upper().replace("$", "")
        if not self.is_configured():
            return {
                "status": "UNAVAILABLE",
                "reason": "TAVILY_API_ERROR",
                "ticker": ticker,
                "message": "Tavily API no configurada para extracción de consenso.",
                "snippets": []
            }

        try:
            query = f"{ticker} stock price target analyst consensus ratings Wall Street TipRanks"
            response = self._client.search(
                query=query,
                search_depth="advanced",
                max_results=3,
                include_domains=["tipranks.com", "marketwatch.com", "finance.yahoo.com", "cnbc.com"]
            )
            
            snippets = [
                r.get("content", "") 
                for r in response.get("results", []) 
                if r.get("content")
            ]
            
            if not snippets:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "TAVILY_API_ERROR",
                    "ticker": ticker,
                    "message": f"No se encontraron reportes públicos de consenso para {ticker}.",
                    "snippets": []
                }

            return {
                "status": "SUCCESS",
                "ticker": ticker,
                "source": "Wall Street Analyst Aggregation (via Tavily)",
                "snippets": snippets
            }
        except Exception as e:
            logger.warning(f"Error consultando consenso de analistas para {ticker}: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": "TAVILY_API_ERROR",
                "ticker": ticker,
                "message": f"Fallo al recuperar consenso: {str(e)}",
                "snippets": []
            }
