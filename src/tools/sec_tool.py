import time
import logging
import requests
from typing import Dict, Any, List, Union
from src.config import settings

logger = logging.getLogger(__name__)

class SECTool:
    """
    Extractor de filings y movimientos regulatorios en la SEC EDGAR.
    Implementa protocolo Fail-Closed y patrón Circuit Breaker para protección contra 429 y caídas.
    Bajo ninguna circunstancia genera datos sintéticos ni filings falsos.
    """
    def __init__(self, user_agent: str = settings.SEC_USER_AGENT):
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self._ticker_map: Dict[str, str] = {}
        # Estado del Circuit Breaker
        self.circuit_open: bool = False
        self.last_failure_timestamp: float = 0.0
        self.cooldown_period: float = 30.0  # segundos

    def _check_circuit(self) -> bool:
        """Verifica si el circuito está abierto o si ya expiró el periodo de enfriamiento."""
        if self.circuit_open:
            if time.time() - self.last_failure_timestamp > self.cooldown_period:
                logger.info("[CIRCUIT BREAKER SEC]: Enfriamiento finalizado. Circuito HALF-OPEN.")
                self.circuit_open = False
                return True
            return False
        return True

    def _trip_circuit(self, reason: str) -> None:
        """Abre el circuito preventivo ante errores críticos o 429 Rate Limits."""
        self.circuit_open = True
        self.last_failure_timestamp = time.time()
        logger.warning(f"[CIRCUIT BREAKER SEC ACTIVADO]: {reason}. Modo Fail-Closed activo.")

    def _get_cik(self, ticker: str) -> str:
        """Obtiene el CIK paddeado a 10 dígitos requerido por la API de la SEC."""
        ticker = ticker.upper().replace("$", "")
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
                elif res.status_code in [429, 403]:
                    self._trip_circuit(f"SEC HTTP {res.status_code} en índice de tickers")
            except Exception as e:
                logger.warning(f"No se pudo descargar el índice de tickers SEC: {e}")
        
        return self._ticker_map.get(ticker, "")

    def get_insider_trades(self, ticker: str, max_filings: int = 5) -> Dict[str, Any]:
        """
        Recupera transacciones de insiders (Form 4) desde SEC EDGAR.
        Protocolo Fail-Closed: ante fallas de API devuelve status UNAVAILABLE sin inventar registros.
        """
        ticker = ticker.upper().replace("$", "")
        if not self._check_circuit():
            return {
                "status": "UNAVAILABLE",
                "reason": "SEC_EDGAR_RATE_LIMIT",
                "ticker": ticker,
                "message": "SEC EDGAR en periodo de enfriamiento por rate limit previo."
            }

        cik = self._get_cik(ticker)
        if not cik:
            return {
                "status": "UNAVAILABLE",
                "reason": "CIK_NOT_FOUND",
                "ticker": ticker,
                "message": f"No se encontró un CIK oficial para el símbolo {ticker} en el directorio de la SEC."
            }

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            res = requests.get(url, headers=self.headers, timeout=6)
            if res.status_code == 429:
                self._trip_circuit("HTTP 429 Too Many Requests de SEC EDGAR")
                return {
                    "status": "UNAVAILABLE",
                    "reason": "SEC_EDGAR_RATE_LIMIT",
                    "ticker": ticker,
                    "message": "Rate limit (HTTP 429) excedido en SEC EDGAR."
                }
            elif res.status_code == 403:
                self._trip_circuit("HTTP 403 Forbidden de SEC EDGAR")
                return {
                    "status": "UNAVAILABLE",
                    "reason": "CONNECTION_ERROR",
                    "ticker": ticker,
                    "message": "Acceso denegado (HTTP 403) por SEC EDGAR. Verifique User-Agent."
                }
            elif res.status_code != 200:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "CONNECTION_ERROR",
                    "ticker": ticker,
                    "message": f"SEC EDGAR devolvió código de error HTTP {res.status_code}."
                }

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

            return {
                "status": "SUCCESS",
                "ticker": ticker,
                "trades": trades,
                "count": len(trades),
                "message": "Transacciones Form 4 recuperadas exitosamente." if trades else "Sin registros recientes de Form 4."
            }

        except Exception as e:
            self._trip_circuit(f"Timeout o excepción en SEC: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": "CONNECTION_ERROR",
                "ticker": ticker,
                "message": f"Fallo de conexión con SEC EDGAR: {str(e)}"
            }

    def get_latest_filing_summary(self, ticker: str) -> Dict[str, Any]:
        """
        Extrae metadatos del reporte anual (10-K) o trimestral (10-Q) más reciente.
        Protocolo Fail-Closed: devuelve status UNAVAILABLE si no es accesible.
        """
        ticker = ticker.upper().replace("$", "")
        cik = self._get_cik(ticker)
        if not cik:
            return {
                "status": "UNAVAILABLE",
                "reason": "CIK_NOT_FOUND",
                "ticker": ticker,
                "message": f"CIK no encontrado para {ticker}."
            }

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            res = requests.get(url, headers=self.headers, timeout=6)
            if res.status_code == 429:
                self._trip_circuit("HTTP 429 en filing summary")
                return {
                    "status": "UNAVAILABLE",
                    "reason": "SEC_EDGAR_RATE_LIMIT",
                    "ticker": ticker,
                    "message": "Rate limit (HTTP 429) en SEC EDGAR."
                }
            elif res.status_code != 200:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "CONNECTION_ERROR",
                    "ticker": ticker,
                    "message": f"SEC EDGAR devolvió código HTTP {res.status_code}."
                }

            data = res.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            
            for i, form in enumerate(forms):
                if form in ["10-K", "10-Q"]:
                    return {
                        "status": "SUCCESS",
                        "ticker": ticker,
                        "entity_name": data.get("name", ticker),
                        "latest_form": form,
                        "filing_date": dates[i] if i < len(dates) else "N/A",
                        "sic": data.get("sic", "N/A"),
                        "sic_description": data.get("sicDescription", "N/A")
                    }
            return {
                "status": "UNAVAILABLE",
                "reason": "CONNECTION_ERROR",
                "ticker": ticker,
                "message": "No se encontraron reportes 10-K o 10-Q recientes en el archivo oficial."
            }
        except Exception as e:
            return {
                "status": "UNAVAILABLE",
                "reason": "CONNECTION_ERROR",
                "ticker": ticker,
                "message": f"Error consultando filing summary: {str(e)}"
            }
