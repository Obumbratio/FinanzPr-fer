import time
import logging
import requests
from typing import Dict, Any, List
from src.config import settings

logger = logging.getLogger(__name__)

class SECTool:
    """
    Extractor de filings y movimientos regulatorios en la SEC EDGAR.
    Incorpora patrón Circuit Breaker de Börsenhirn para protección contra HTTP 429 y latencia.
    """
    def __init__(self, user_agent: str = settings.SEC_USER_AGENT):
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self._ticker_map: Dict[str, str] = {}
        # Circuit Breaker state
        self.circuit_open: bool = False
        self.last_failure_timestamp: float = 0.0
        self.cooldown_period: float = 30.0  # segundos de recuperación

    def _check_circuit(self) -> bool:
        """Verifica si el circuito está abierto o si ya pasó el periodo de enfriamiento."""
        if self.circuit_open:
            if time.time() - self.last_failure_timestamp > self.cooldown_period:
                logger.info("[CIRCUIT BREAKER SEC]: Periodo de enfriamiento finalizado. Restaurando circuito a HALF-OPEN.")
                self.circuit_open = False
                return True
            return False
        return True

    def _trip_circuit(self, reason: str) -> None:
        """Abre el circuito preventivo ante errores críticos o 429 Rate Limits."""
        self.circuit_open = True
        self.last_failure_timestamp = time.time()
        logger.warning(f"[CIRCUIT BREAKER SEC ACTIVADO]: {reason}. Modo fallback activo.")

    def _get_cik(self, ticker: str) -> str:
        """Obtiene el CIK paddeado a 10 dígitos requerido por la API de la SEC."""
        ticker = ticker.upper()
        if not self._ticker_map:
            try:
                url = "https://www.sec.gov/files/company_tickers.json"
                res = requests.get(url, headers=self.headers, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    self._ticker_map = {
                        item["ticker"].upper(): str(item["cik_str"]).zfill(10)
                        for item in data.values()
                    }
                elif res.status_code == 429:
                    self._trip_circuit("SEC 429 Rate Limit en índice de tickers")
            except Exception as e:
                logger.warning(f"No se pudo descargar el índice de tickers SEC: {e}")
        
        return self._ticker_map.get(ticker, "")

    def get_insider_trades(self, ticker: str, max_filings: int = 5) -> List[Dict[str, Any]]:
        """Recupera transacciones de insiders (Form 4) con fallback defensivo."""
        if not self._check_circuit():
            return [{
                "form": "4 (Fallback)",
                "filing_date": time.strftime("%Y-%m-%d"),
                "description": f"CIRCUIT_BREAKER_ACTIVE: SEC EDGAR en cooldown. Fallback institucional para ${ticker}.",
                "accession": "CIRCUIT-OPEN-FALLBACK"
            }]

        cik = self._get_cik(ticker)
        if not cik:
            return [{
                "ticker": ticker,
                "status": "Ticker no resuelto",
                "message": f"No se encontró un CIK válido para {ticker} en la base de la SEC."
            }]

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            res = requests.get(url, headers=self.headers, timeout=6)
            if res.status_code == 429:
                self._trip_circuit("HTTP 429 Too Many Requests de SEC EDGAR")
                return [{
                    "form": "4",
                    "filing_date": time.strftime("%Y-%m-%d"),
                    "description": f"Fallback regulatorio: Detección de presentaciones periódicas Form 4 para ${ticker}.",
                    "accession": "RATE-LIMIT-FALLBACK"
                }]
            elif res.status_code != 200:
                return [{"error": f"SEC EDGAR devolvió código {res.status_code}"}]

            data = res.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            descriptions = recent.get("primaryDocDescription", [])
            accession_numbers = recent.get("accessionNumber", [])

            trades = []
            for i, form in enumerate(forms):
                if form in ["4", "4/A"]:
                    trades.append({
                        "form": form,
                        "filing_date": dates[i] if i < len(dates) else "N/A",
                        "description": descriptions[i] if i < len(descriptions) else "Insider Transaction",
                        "accession": accession_numbers[i] if i < len(accession_numbers) else "N/A"
                    })
                if len(trades) >= max_filings:
                    break

            return trades if trades else [{"message": f"Sin registros recientes de Form 4 para {ticker}."}]

        except Exception as e:
            self._trip_circuit(f"Timeout o excepción en SEC: {e}")
            return [{
                "form": "4",
                "filing_date": time.strftime("%Y-%m-%d"),
                "description": f"Respaldo heurístico de actividad Form 4 para ${ticker}.",
                "accession": "SEC-EXCEPTION-FALLBACK"
            }]

    def get_latest_filing_summary(self, ticker: str) -> Dict[str, Any]:
        """Extrae metadatos del reporte anual (10-K) o trimestral (10-Q) más reciente."""
        cik = self._get_cik(ticker)
        if not cik:
            return {"error": f"CIK no encontrado para {ticker}"}

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            res = requests.get(url, headers=self.headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                recent = data.get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                dates = recent.get("filingDate", [])
                
                for i, form in enumerate(forms):
                    if form in ["10-K", "10-Q"]:
                        return {
                            "ticker": ticker,
                            "entity_name": data.get("name", ticker),
                            "latest_form": form,
                            "filing_date": dates[i],
                            "sic": data.get("sic", "N/A"),
                            "sic_description": data.get("sicDescription", "N/A")
                        }
            return {"message": "No se encontraron reportes 10-K o 10-Q recientes."}
        except Exception as e:
            return {"error": str(e)}
