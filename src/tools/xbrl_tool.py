import time
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

XBRL_CONCEPTS = {
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities"
    ],
    "net_income": [
        "NetIncomeLoss"
    ],
    "accounts_receivable": [
        "AccountsReceivableNetCurrent"
    ],
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "inventory": [
        "InventoryNet"
    ],
    "cost_of_revenue": [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
    ],
    "total_assets": [
        "Assets"
    ],
    "total_liabilities": [
        "Liabilities"
    ],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
    ],
    "total_debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
    ],
}


class XBRLTool:
    """
    Herramienta de extracción de métricas fundamentales y balances desde la API pública XBRL de SEC EDGAR.
    Arquitectura Fail-Closed: nunca fabrica ni asume cifras contables.
    Aplica cooldown de 0.12s para respetar la tasa de 10 req/s de la SEC.
    """
    def __init__(self, user_agent: str = settings.SEC_USER_AGENT):
        self.headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate"
        }
        self._ticker_map: Dict[str, str] = {}

    def get_cik(self, ticker: str) -> str:
        """Obtiene el CIK paddeado a 10 dígitos requerido por la API XBRL de la SEC."""
        clean_ticker = ticker.upper().replace("$", "").strip()
        if not self._ticker_map:
            try:
                time.sleep(0.12)
                url = "https://www.sec.gov/files/company_tickers.json"
                res = requests.get(url, headers=self.headers, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    self._ticker_map = {
                        str(item["ticker"]).upper(): str(item["cik_str"]).zfill(10)
                        for item in data.values()
                    }
                else:
                    logger.warning(f"SEC ticker index returned HTTP {res.status_code}")
            except Exception as e:
                logger.warning(f"Error fetching SEC company tickers index: {e}")

        return self._ticker_map.get(clean_ticker, "")

    def _query_concept(self, cik_padded: str, tag: str) -> Optional[Dict[str, Any]]:
        """Consulta un tag GAAP específico en la API companyconcept."""
        try:
            time.sleep(0.12)
            url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik_padded}/us-gaap/{tag}.json"
            res = requests.get(url, headers=self.headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                units = data.get("units", {})
                usd_entries = units.get("USD", [])
                filings = [x for x in usd_entries if x.get("form") in ("10-Q", "10-K")]
                if filings:
                    # Priorizar 10-Q más reciente; si no hay 10-Q, usar 10-K
                    ten_q = [x for x in filings if x.get("form") == "10-Q"]
                    chosen = ten_q if ten_q else filings
                    chosen.sort(key=lambda x: x.get("end", ""), reverse=True)
                    return chosen[0]
            elif res.status_code == 404:
                return None
            else:
                logger.debug(f"Tag {tag} for CIK {cik_padded} returned status {res.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Exception querying XBRL concept {tag}: {e}")
            return None

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Recupera fundamentales y balance desde SEC EDGAR XBRL para un ticker bursátil.
        Calcula ratios de calidad de utilidades, DSO, DIO, deuda neta y margen bruto.
        """
        clean_ticker = ticker.upper().replace("$", "").strip()
        as_of_ts = datetime.now(timezone.utc).isoformat()

        cik = self.get_cik(clean_ticker)
        if not cik:
            return {
                "status": "UNAVAILABLE",
                "source": "SEC EDGAR XBRL CompanyConcept API",
                "as_of": as_of_ts,
                "ticker": clean_ticker,
                "reason": f"CIK not found for ticker '{clean_ticker}' in SEC directory.",
                "period": {},
                "raw_values": {},
                "derived_metrics": {},
                "interpretation": {},
                "concepts_unavailable": list(XBRL_CONCEPTS.keys())
            }

        raw_values: Dict[str, Optional[Dict[str, Any]]] = {}
        concepts_unavailable: List[str] = []

        # Paso 1: Consultar los conceptos con sus variantes
        for concept_name, tag_variants in XBRL_CONCEPTS.items():
            best_entry = None
            for tag in tag_variants:
                entry = self._query_concept(cik, tag)
                if entry:
                    if best_entry is None or entry.get("end", "") > best_entry.get("end", ""):
                        best_entry = entry
                        # Si ya tenemos un 10-Q reciente del año corriente, podemos evitar seguir consultando variantes
                        if entry.get("form") == "10-Q":
                            break

            if best_entry and best_entry.get("val") is not None:
                raw_values[concept_name] = {
                    "value": float(best_entry["val"]),
                    "end": best_entry.get("end"),
                    "form": best_entry.get("form"),
                    "fp": best_entry.get("fp"),
                    "fy": best_entry.get("fy"),
                }
            else:
                raw_values[concept_name] = None
                concepts_unavailable.append(concept_name)

        # Paso 2: Determinar período global representativo
        all_ends = [v["end"] for v in raw_values.values() if v and v.get("end")]
        most_recent_end = max(all_ends) if all_ends else None

        # Determinar formulario y fiscal_period asociado al most_recent_end
        sample_entry = next((v for v in raw_values.values() if v and v.get("end") == most_recent_end), None)
        most_recent_form = sample_entry.get("form", "10-Q") if sample_entry else "10-Q"
        fp_str = sample_entry.get("fp") if sample_entry else None
        fy_str = sample_entry.get("fy") if sample_entry else None
        fiscal_period = f"{fp_str} {fy_str}".strip() if (fp_str or fy_str) else None

        # Paso 3: Calcular métricas derivadas
        val_ocf = raw_values.get("operating_cash_flow")
        val_ni = raw_values.get("net_income")
        val_ar = raw_values.get("accounts_receivable")
        val_rev = raw_values.get("revenue")
        val_inv = raw_values.get("inventory")
        val_cor = raw_values.get("cost_of_revenue")
        val_cash = raw_values.get("cash_and_equivalents")
        val_debt = raw_values.get("total_debt")

        ocf = val_ocf["value"] if val_ocf else None
        ni = val_ni["value"] if val_ni else None
        ar = val_ar["value"] if val_ar else None
        rev = val_rev["value"] if val_rev else None
        inv = val_inv["value"] if val_inv else None
        cor = val_cor["value"] if val_cor else None
        cash = val_cash["value"] if val_cash else None
        debt = val_debt["value"] if val_debt else None

        # OCF / NI ratio (calidad de conversión de utilidades)
        if ocf is not None and ni is not None and ni != 0:
            ocf_ni_ratio = round(ocf / ni, 2)
        else:
            ocf_ni_ratio = None

        # DSO (Days Sales Outstanding) = (AR / Revenue) * 90 (trimestral)
        if ar is not None and rev is not None and rev != 0:
            dso = round((ar / rev) * 90, 1)
        else:
            dso = None

        # DIO (Days Inventory Outstanding) = (Inventory / Cost of Revenue) * 90
        if inv is not None and cor is not None and cor != 0:
            dio = round((inv / cor) * 90, 1)
        else:
            dio = None

        # Deuda Neta = Total Debt - Cash
        if debt is not None and cash is not None:
            net_debt = round(debt - cash, 2)
        else:
            net_debt = None

        # Margen Bruto = (Revenue - Cost of Revenue) / Revenue
        if rev is not None and cor is not None and rev != 0:
            gross_margin = round((rev - cor) / rev, 4)
        else:
            gross_margin = None

        # Paso 4: Interpretación institucional
        if ocf_ni_ratio is not None:
            if ocf_ni_ratio > 0.8:
                ocf_interp = "HEALTHY"
            elif ocf_ni_ratio < 0.5:
                ocf_interp = "INVESTIGATE"
            else:
                ocf_interp = "MODERATE"
        else:
            ocf_interp = "UNKNOWN"

        if net_debt is not None:
            if net_debt < 0:
                debt_interp = "CASH_RICH"
            elif net_debt > 0:
                debt_interp = "LEVERAGED"
            else:
                debt_interp = "BALANCED"
        else:
            debt_interp = "UNKNOWN"

        # Paso 5: Estado general
        if not concepts_unavailable:
            status = "SUCCESS"
        elif len(concepts_unavailable) < len(XBRL_CONCEPTS):
            status = "PARTIAL"
        else:
            status = "UNAVAILABLE"

        return {
            "status": status,
            "source": "SEC EDGAR XBRL CompanyConcept API",
            "as_of": as_of_ts,
            "ticker": clean_ticker,
            "period": {
                "end_date": most_recent_end,
                "form": most_recent_form,
                "fiscal_period": fiscal_period,
            },
            "raw_values": raw_values,
            "derived_metrics": {
                "ocf_ni_ratio": ocf_ni_ratio,
                "dso_days": dso,
                "dio_days": dio,
                "net_debt_usd": net_debt,
                "gross_margin": gross_margin,
            },
            "interpretation": {
                "ocf_ni_ratio": ocf_interp,
                "net_debt": debt_interp,
            },
            "concepts_unavailable": concepts_unavailable
        }


# Instancia compartida y función de conveniencia
_xbrl_tool_instance = XBRLTool()

def get_fundamentals(ticker: str) -> Dict[str, Any]:
    """Punto de entrada modular para la consulta de fundamentales XBRL."""
    return _xbrl_tool_instance.get_fundamentals(ticker)
