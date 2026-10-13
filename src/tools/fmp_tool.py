"""
FMP Tool — Financial Modeling Prep API
Direct HTTP client via requests (no heavy SDK dependencies).
Provides: Income Statement (quarterly margins, YoY growth),
Earnings Surprises (actual vs estimate, beat streak),
Revenue by Segment (product and geographic breakdowns),
Company Profile (sector, industry, market cap, beta).
"""

import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from src.config import settings

logger = logging.getLogger(__name__)

class FMPTool:
    """
    Cliente institucional para Financial Modeling Prep (FMP).
    Compatible con endpoints estables de FMP (2026+) con fallback automático a v3.
    Aplica protocolo Fail-Closed y degradación elegante ante cuotas o planes gratuitos.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.FMP_API_KEY
        self.base_url_stable = "https://financialmodelingprep.com/stable"
        self.base_url_v3 = "https://financialmodelingprep.com/api/v3"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "tu_clave_fmp_aqui")

    def _get(self, endpoint_stable: str, endpoint_v3: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Ejecuta petición HTTP con fallback de stable a v3 y manejo fail-closed."""
        if not self.is_configured():
            return None

        q_params = params.copy() if params else {}
        q_params["apikey"] = self.api_key

        # 1. Intentar endpoint stable
        url_stable = f"{self.base_url_stable}/{endpoint_stable}"
        try:
            resp = requests.get(url_stable, params=q_params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (402, 403):
                logger.warning(f"FMP stable returned {resp.status_code} for {endpoint_stable}")
        except Exception as e:
            logger.warning(f"Error en FMP stable {endpoint_stable}: {e}")

        # 2. Fallback a endpoint v3 si está especificado
        if endpoint_v3:
            url_v3 = f"{self.base_url_v3}/{endpoint_v3}"
            try:
                resp = requests.get(url_v3, params=q_params, timeout=10)
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.warning(f"Error en FMP v3 {endpoint_v3}: {e}")

        return None

    def get_income_statement(self, ticker: str) -> Dict[str, Any]:
        """
        Extrae los últimos 4 trimestres del estado de resultados:
        revenue, grossProfit, operatingIncome, netIncome, epsDiluted, márgenes y crecimiento YoY.
        """
        clean_ticker = ticker.upper().replace("$", "").strip()
        if not self.is_configured():
            return {"status": "UNAVAILABLE", "reason": "FMP_API_KEY not configured", "ticker": clean_ticker}

        data = self._get(
            f"income-statement",
            f"income-statement/{clean_ticker}",
            {"symbol": clean_ticker, "period": "quarter", "limit": 4}
        )

        if not data or not isinstance(data, list) or len(data) == 0:
            return {"status": "UNAVAILABLE", "reason": f"No quarterly income statement found for {clean_ticker}", "ticker": clean_ticker}

        latest = data[0]
        rev = latest.get("revenue", 0)
        gp = latest.get("grossProfit", 0)
        oi = latest.get("operatingIncome", 0)
        ni = latest.get("netIncome", 0)
        eps_d = latest.get("epsDiluted") if latest.get("epsDiluted") is not None else latest.get("eps", 0.0)

        gross_margin = round(gp / rev, 4) if rev else 0.0
        operating_margin = round(oi / rev, 4) if rev else 0.0

        # Crecimiento YoY si tenemos 4 trimestres (comparar Q actual con Q de hace 1 año)
        yoy_growth: Dict[str, Optional[float]] = {
            "revenue_growth": None,
            "operating_income_growth": None,
            "eps_growth": None
        }

        if len(data) >= 4:
            prev_y = data[3]
            prev_rev = prev_y.get("revenue")
            prev_oi = prev_y.get("operatingIncome")
            prev_eps = prev_y.get("epsDiluted") if prev_y.get("epsDiluted") is not None else prev_y.get("eps")

            if prev_rev and prev_rev != 0:
                yoy_growth["revenue_growth"] = round(((rev - prev_rev) / abs(prev_rev)), 4)
            if prev_oi and prev_oi != 0:
                yoy_growth["operating_income_growth"] = round(((oi - prev_oi) / abs(prev_oi)), 4)
            if prev_eps and prev_eps != 0 and eps_d is not None:
                yoy_growth["eps_growth"] = round(((eps_d - prev_eps) / abs(prev_eps)), 4)

        period_label = f"{latest.get('period', 'Q')} {latest.get('calendarYear', latest.get('fiscalYear', ''))}".strip()

        return {
            "status": "SUCCESS",
            "source": "Financial Modeling Prep",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "ticker": clean_ticker,
            "period": period_label,
            "latest_quarter": {
                "revenue": rev,
                "gross_profit": gp,
                "operating_income": oi,
                "net_income": ni,
                "eps_diluted": eps_d,
                "gross_margin": gross_margin,
                "operating_margin": operating_margin,
            },
            "yoy_growth": yoy_growth,
            "quarters": data[:4]
        }

    def get_earnings_surprises(self, ticker: str) -> Dict[str, Any]:
        """
        Historial de EPS y Revenue actual vs estimado para los últimos 4 trimestres.
        Calcula el porcentaje de sorpresa y la racha de trimestres batiendo estimados (beat streak).
        """
        clean_ticker = ticker.upper().replace("$", "").strip()
        if not self.is_configured():
            return {"status": "UNAVAILABLE", "reason": "FMP_API_KEY not configured", "ticker": clean_ticker}

        data = self._get(
            f"earnings",
            f"earnings-surprises/{clean_ticker}",
            {"symbol": clean_ticker}
        )

        if not data or not isinstance(data, list):
            return {"status": "UNAVAILABLE", "reason": f"No earnings surprise data for {clean_ticker}", "ticker": clean_ticker}

        # Filtrar solo presentaciones pasadas que contengan resultado real
        past_earnings = [d for d in data if d.get("epsActual") is not None or d.get("actualEarningResult") is not None]

        if not past_earnings:
            return {"status": "UNAVAILABLE", "reason": f"No reported earnings history for {clean_ticker}", "ticker": clean_ticker}

        surprises: List[Dict[str, Any]] = []
        beat_streak = 0
        streak_broken = False
        surprise_pcts: List[float] = []

        for item in past_earnings[:4]:
            eps_act = item.get("epsActual", item.get("actualEarningResult"))
            eps_est = item.get("epsEstimated", item.get("estimatedEarning"))
            rev_act = item.get("revenueActual")
            rev_est = item.get("revenueEstimated")
            date_str = item.get("date", "")

            surprise_pct = 0.0
            if eps_act is not None and eps_est is not None and eps_est != 0:
                surprise_pct = round(((eps_act - eps_est) / abs(eps_est)) * 100.0, 2)
                surprise_pcts.append(surprise_pct)

            rev_surprise_pct = None
            if rev_act is not None and rev_est is not None and rev_est != 0:
                rev_surprise_pct = round(((rev_act - rev_est) / abs(rev_est)) * 100.0, 2)

            # Racha consecutiva de superación de estimados
            if eps_act is not None and eps_est is not None:
                if eps_act >= eps_est and not streak_broken:
                    beat_streak += 1
                else:
                    streak_broken = True

            surprises.append({
                "date": date_str,
                "eps_estimated": eps_est,
                "eps_actual": eps_act,
                "surprise_pct": surprise_pct,
                "revenue_estimated": rev_est,
                "revenue_actual": rev_act,
                "revenue_surprise_pct": rev_surprise_pct
            })

        avg_surprise = round(sum(surprise_pcts) / len(surprise_pcts), 2) if surprise_pcts else 0.0

        return {
            "status": "SUCCESS",
            "source": "Financial Modeling Prep",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "ticker": clean_ticker,
            "surprises": surprises,
            "beat_streak": beat_streak,
            "average_surprise_pct": avg_surprise
        }

    def get_revenue_by_segment(self, ticker: str) -> Dict[str, Any]:
        """
        Extrae la segmentación de ingresos por producto/línea de negocio y por geografía.
        Calcula la concentración de ingresos del segmento principal.
        """
        clean_ticker = ticker.upper().replace("$", "").strip()
        if not self.is_configured():
            return {"status": "UNAVAILABLE", "reason": "FMP_API_KEY not configured", "ticker": clean_ticker}

        prod_data = self._get("revenue-product-segmentation", "revenue-product-segmentation", {"symbol": clean_ticker, "structure": "flat"})
        geo_data = self._get("revenue-geographic-segmentation", "revenue-geographic-segmentation", {"symbol": clean_ticker, "structure": "flat"})

        product_segments: Dict[str, float] = {}
        geographic_segments: Dict[str, float] = {}

        if prod_data and isinstance(prod_data, list) and len(prod_data) > 0:
            product_segments = prod_data[0].get("data", {})

        if geo_data and isinstance(geo_data, list) and len(geo_data) > 0:
            geographic_segments = geo_data[0].get("data", {})

        if not product_segments and not geographic_segments:
            return {
                "status": "UNAVAILABLE",
                "reason": "Segment data not available in free tier or company does not report segment breakdown",
                "ticker": clean_ticker
            }

        total_rev = sum(product_segments.values()) if product_segments else sum(geographic_segments.values())
        concentration_note = ""

        if product_segments and total_rev > 0:
            top_seg = max(product_segments.items(), key=lambda x: x[1])
            pct = (top_seg[1] / total_rev) * 100.0
            concentration_note = f"Top product segment '{top_seg[0]}' represents {pct:.1f}% of total segment revenue"
        elif geographic_segments and total_rev > 0:
            top_geo = max(geographic_segments.items(), key=lambda x: x[1])
            pct = (top_geo[1] / total_rev) * 100.0
            concentration_note = f"Top geographic region '{top_geo[0]}' represents {pct:.1f}% of total segment revenue"

        status = "SUCCESS" if (product_segments and geographic_segments) else "PARTIAL"

        return {
            "status": status,
            "source": "Financial Modeling Prep",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "ticker": clean_ticker,
            "product_segments": product_segments,
            "geographic_segments": geographic_segments,
            "total_revenue": total_rev,
            "concentration_note": concentration_note
        }

    def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """
        Perfil corporativo: sector, industria, número de empleados, capitalización bursátil, beta y descripción.
        """
        clean_ticker = ticker.upper().replace("$", "").strip()
        if not self.is_configured():
            return {"status": "UNAVAILABLE", "reason": "FMP_API_KEY not configured", "ticker": clean_ticker}

        data = self._get("profile", f"profile/{clean_ticker}", {"symbol": clean_ticker})

        if not data or not isinstance(data, list) or len(data) == 0:
            return {"status": "UNAVAILABLE", "reason": f"No profile found for {clean_ticker}", "ticker": clean_ticker}

        item = data[0]
        employees_raw = item.get("fullTimeEmployees")
        employees = None
        if employees_raw:
            try:
                employees = int(str(employees_raw).replace(",", "").strip())
            except (ValueError, TypeError):
                employees = None

        desc = item.get("description", "")
        short_desc = desc[:200] + ("..." if len(desc) > 200 else "")

        return {
            "status": "SUCCESS",
            "source": "Financial Modeling Prep",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "ticker": clean_ticker,
            "profile": {
                "company_name": item.get("companyName", clean_ticker),
                "sector": item.get("sector", "N/A"),
                "industry": item.get("industry", "N/A"),
                "employees": employees,
                "market_cap": item.get("marketCap", 0),
                "beta": item.get("beta", 1.0),
                "description": short_desc
            }
        }

# Instancia singleton para uso modular
fmp_tool = FMPTool()
