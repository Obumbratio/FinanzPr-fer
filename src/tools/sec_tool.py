import logging
import requests
from typing import Dict, Any, List
from src.config import settings

logger = logging.getLogger(__name__)

class SECTool:
    """
    Extractor de filings y movimientos regulatorios en la SEC EDGAR.
    Permite auditar compras/ventas internas (Form 4) y factores de riesgo (10-K).
    """
    def __init__(self, user_agent: str = settings.SEC_USER_AGENT):
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self._ticker_map: Dict[str, str] = {}

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
            except Exception as e:
                logger.warning(f"No se pudo descargar el índice de tickers SEC: {e}")
        
        return self._ticker_map.get(ticker, "")

    def get_insider_trades(self, ticker: str, max_filings: int = 5) -> List[Dict[str, Any]]:
        """Recupera las transacciones de insiders más recientes registradas en Form 4."""
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
            if res.status_code != 200:
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
            logger.error(f"Error consultando SEC para {ticker}: {e}")
            return [{"error": str(e)}]

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
