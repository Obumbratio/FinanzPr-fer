import time
import logging
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse
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
        Extrae fragmentos fácticos del consenso de analistas de Wall Street, ratings y precios objetivo
        mediante múltiples consultas dirigidas en Tavily.
        Protocolo Fail-Closed: si no hay datos o falla Tavily, reporta status UNAVAILABLE sin inventar cifras.
        """
        clean_ticker = ticker.upper().replace("$", "").strip()
        if not clean_ticker:
            return {
                "status": "UNAVAILABLE",
                "reason": "EMPTY_TICKER",
                "ticker": clean_ticker
            }

        if not self.is_configured():
            return {
                "status": "UNAVAILABLE",
                "reason": "TAVILY_API_ERROR",
                "ticker": clean_ticker,
                "message": "Tavily API no configurada para extracción de consenso."
            }

        queries = [
            f"{clean_ticker} stock analyst price target consensus 2026",
            f"{clean_ticker} analyst rating buy sell hold count Wall Street",
            f"{clean_ticker} earnings estimate EPS revenue forecast next quarter",
        ]

        domains = [
            "tipranks.com", "marketbeat.com", "finance.yahoo.com",
            "cnbc.com", "benzinga.com", "marketwatch.com",
            "bloomberg.com", "reuters.com", "wsj.com"
        ]

        search_results: List[Dict[str, Any]] = []
        total_raw_count = 0

        for idx, q in enumerate(queries):
            if idx > 0:
                time.sleep(0.5)

            try:
                response = self._client.search(
                    query=q,
                    search_depth="advanced",
                    max_results=4,
                    include_domains=domains
                )
                raw_items = response.get("results", [])
                query_results = []
                for item in raw_items:
                    u = item.get("url", "")
                    snip = item.get("content", "").strip()
                    if not snip:
                        continue
                    domain = urlparse(u).netloc if u else "N/A"
                    query_results.append({
                        "title": item.get("title", "Sin título"),
                        "url": u,
                        "snippet": snip,
                        "source_domain": domain
                    })

                total_raw_count += len(query_results)
                search_results.append({
                    "query": q,
                    "results": query_results
                })
            except Exception as e:
                logger.warning(f"Error en consulta Tavily para '{q}': {e}")
                search_results.append({
                    "query": q,
                    "results": []
                })

        if total_raw_count == 0:
            return {
                "status": "UNAVAILABLE",
                "reason": "No analyst consensus data found via Tavily",
                "ticker": clean_ticker
            }

        return {
            "status": "SUCCESS",
            "source": "Tavily Search — Wall Street Analyst Consensus",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "ticker": clean_ticker,
            "search_results": search_results,
            "raw_result_count": total_raw_count,
            "interpretation_note": (
                "These are raw search results. The orchestrator LLM must extract and synthesize "
                "price targets, ratings, and EPS estimates from the snippets. Do NOT invent data not present in the snippets."
            )
        }

    def get_recommendation_trends(self, ticker: str) -> Dict[str, Any]:
        """
        Retrieves analyst recommendation trend history from Finnhub.
        Endpoint: https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={key}
        Returns monthly breakdown of strongBuy, buy, hold, sell, strongSell over last 6 months.
        Protocol: Fail-closed with graceful degradation if FINNHUB_API_KEY is missing.
        """
        clean_ticker = ticker.upper().replace("$", "").strip()
        finnhub_key = settings.FINNHUB_API_KEY
        if not finnhub_key or finnhub_key == "tu_clave_finnhub_aqui":
            return {
                "status": "UNAVAILABLE",
                "reason": "FINNHUB_API_KEY not configured — this is optional",
                "ticker": clean_ticker
            }

        url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={clean_ticker}&token={finnhub_key}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not data or not isinstance(data, list):
                return {
                    "status": "UNAVAILABLE",
                    "reason": f"No recommendation trend data found for {clean_ticker}",
                    "ticker": clean_ticker
                }

            sorted_data = sorted(data, key=lambda x: x.get("period", ""), reverse=True)
            latest = sorted_data[0]
            latest_breakdown = {
                "strong_buy": latest.get("strongBuy", 0),
                "buy": latest.get("buy", 0),
                "hold": latest.get("hold", 0),
                "sell": latest.get("sell", 0),
                "strong_sell": latest.get("strongSell", 0),
                "period": latest.get("period", "")
            }
            total_analysts = sum([
                latest_breakdown["strong_buy"],
                latest_breakdown["buy"],
                latest_breakdown["hold"],
                latest_breakdown["sell"],
                latest_breakdown["strong_sell"]
            ])

            buys = latest_breakdown["strong_buy"] + latest_breakdown["buy"]
            sells = latest_breakdown["sell"] + latest_breakdown["strong_sell"]
            holds = latest_breakdown["hold"]
            if buys > (holds + sells):
                consensus = "STRONG_BUY" if latest_breakdown["strong_buy"] > latest_breakdown["buy"] else "BUY"
            elif sells > (buys + holds):
                consensus = "SELL"
            else:
                consensus = "HOLD"

            trend_direction = "STABLE"
            if len(sorted_data) >= 3:
                older = sorted_data[2]
                older_buys = older.get("strongBuy", 0) + older.get("buy", 0)
                if buys > older_buys + 2:
                    trend_direction = "IMPROVING"
                elif buys < older_buys - 2:
                    trend_direction = "DETERIORATING"

            return {
                "status": "SUCCESS",
                "source": "Finnhub Recommendation Trends",
                "as_of": datetime.now(timezone.utc).isoformat(),
                "ticker": clean_ticker,
                "trends": sorted_data[:6],
                "latest": latest_breakdown,
                "total_analysts": total_analysts,
                "consensus": consensus,
                "trend_direction": trend_direction
            }
        except Exception as e:
            logger.warning(f"Error en Finnhub recommendation trends para {clean_ticker}: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": f"FINNHUB_API_ERROR: {str(e)}",
                "ticker": clean_ticker
            }

    def get_institutional_flow(self, ticker: str) -> Dict[str, Any]:
        """
        Uses Tavily Search to identify recent 13F institutional ownership trends,
        hedge fund buying/selling patterns, and whale portfolio movements for the target stock.
        Protocol: Fail-closed with graceful degradation.
        """
        clean_ticker = ticker.upper().replace("$", "").strip()
        if not self.is_configured():
            return {
                "status": "UNAVAILABLE",
                "reason": "TAVILY_API_ERROR",
                "ticker": clean_ticker,
                "message": "Tavily API no configurada para extracción de flujo institucional."
            }

        queries = [
            f"{clean_ticker} institutional ownership 13F filing 2026 top holders",
            f"{clean_ticker} hedge fund buying selling whale activity",
        ]

        domains = [
            "whalewisdom.com", "fintel.io", "sec.gov", "finance.yahoo.com",
            "bloomberg.com", "reuters.com", "wsj.com", "cnbc.com", "marketbeat.com"
        ]

        results = []
        for idx, q in enumerate(queries):
            if idx > 0:
                time.sleep(0.4)
            try:
                response = self._client.search(
                    query=q,
                    search_depth="advanced",
                    max_results=3,
                    include_domains=domains
                )
                for item in response.get("results", []):
                    u = item.get("url", "")
                    content = item.get("content", "").strip()
                    if content:
                        results.append({
                            "title": item.get("title", ""),
                            "url": u,
                            "snippet": content,
                            "source_domain": urlparse(u).netloc if u else "N/A"
                        })
            except Exception as e:
                logger.warning(f"Error consultando flujo institucional para '{q}': {e}")

        if not results:
            return {
                "status": "UNAVAILABLE",
                "reason": "No institutional flow data found",
                "ticker": clean_ticker
            }

        return {
            "status": "SUCCESS",
            "source": "SEC 13F & Institutional Whale Tracker (Tavily)",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "ticker": clean_ticker,
            "results": results,
            "interpretation_note": (
                "Raw institutional 13F ownership and hedge fund transaction reports. "
                "The agent must synthesize top holders, net flow direction, and cite sources."
            )
        }
