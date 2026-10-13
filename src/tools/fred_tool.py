"""
FRED Tool — Federal Reserve Economic Data
API gratuita: https://fred.stlouisfed.org/docs/api/fred/
Endpoint: https://api.stlouisfed.org/fred/series/observations
"""

import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.config import settings

logger = logging.getLogger(__name__)

FRED_SERIES = {
    "treasury_10y": "DGS10",       # 10-Year Treasury Constant Maturity Rate
    "treasury_2y": "DGS2",         # 2-Year Treasury Constant Maturity Rate
    "fed_funds_rate": "FEDFUNDS",   # Federal Funds Effective Rate
    "unemployment": "UNRATE",       # Civilian Unemployment Rate
    "cpi_yoy": "CPIAUCSL",          # Consumer Price Index for All Urban Consumers
    "core_pce": "PCEPILFE",         # Core PCE Price Index (Fed's preferred measure)
    "sp500": "SP500",               # S&P 500 index level
    "initial_claims": "ICSA",       # Initial Jobless Claims
}

UNITS = {
    "treasury_10y": "%",
    "treasury_2y": "%",
    "fed_funds_rate": "%",
    "unemployment": "%",
    "cpi_yoy": "%",
    "core_pce": "%",
    "sp500": "points",
    "initial_claims": "claims",
}

class FREDTool:
    """
    Cliente institucional para el servicio de datos económicos FRED (Federal Reserve Bank of St. Louis).
    Extrae tasas del tesoro, inflación, desempleo y clasifica el régimen macroeconómico.
    Aplica protocolo Fail-Closed con degradación elegante.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.FRED_API_KEY
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "tu_clave_fred_aqui")

    def _fetch_series_observations(self, series_id: str, limit: int = 5) -> list:
        """Consulta observaciones para una serie en orden descendente."""
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit
        }
        resp = requests.get(self.base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        raw_obs = data.get("observations", [])
        # Filtrar observaciones no válidas (ej. "." cuando el mercado estuvo cerrado)
        valid_obs = [o for o in raw_obs if o.get("value") and o.get("value").strip() != "."]
        return valid_obs

    def get_macro_indicators(self) -> Dict[str, Any]:
        """
        Consulta las series clave de FRED, calcula el yield spread (10Y - 2Y) y CPI YoY,
        y determina el régimen macroeconómico.
        """
        if not self.is_configured():
            return {
                "status": "UNAVAILABLE",
                "reason": "FRED_API_KEY not configured in environment"
            }

        indicators: Dict[str, Any] = {}
        raw_values: Dict[str, float] = {}

        try:
            for name, series_code in FRED_SERIES.items():
                limit = 18 if name == "cpi_yoy" else 6
                obs_list = self._fetch_series_observations(series_code, limit=limit)
                
                if not obs_list:
                    continue

                latest_obs = obs_list[0]
                try:
                    val = float(latest_obs["value"])
                except (ValueError, TypeError):
                    continue

                obs_date = latest_obs.get("date", "")
                raw_values[name] = val

                if name == "cpi_yoy":
                    # Calcular YoY comparando el dato más reciente con el de hace 12 meses
                    if len(obs_list) >= 13:
                        val_12m = float(obs_list[12]["value"])
                        cpi_calc = round(((val / val_12m) - 1.0) * 100.0, 2)
                        indicators["cpi_yoy"] = {
                            "value": cpi_calc,
                            "date": obs_date,
                            "unit": "%"
                        }
                        raw_values["cpi_yoy"] = cpi_calc
                    else:
                        indicators["cpi_yoy"] = {
                            "value": val,
                            "date": obs_date,
                            "unit": "index"
                        }
                else:
                    indicators[name] = {
                        "value": val,
                        "date": obs_date,
                        "unit": UNITS.get(name, "")
                    }

            # 1. Calcular Yield Spread (10Y - 2Y)
            t10 = raw_values.get("treasury_10y")
            t2 = raw_values.get("treasury_2y")
            yield_spread = None
            if t10 is not None and t2 is not None:
                yield_spread = round(t10 - t2, 2)
                indicators["yield_spread_10y_2y"] = {
                    "value": yield_spread,
                    "interpretation": "NORMAL" if yield_spread >= 0 else "INVERTED",
                    "unit": "%"
                }

            # 2. Macro Regime Assessment
            fed_funds = raw_values.get("fed_funds_rate", 5.0)
            core_pce = raw_values.get("core_pce", 2.5)
            
            if yield_spread is not None and yield_spread < 0:
                regime = "RECESSION_RISK"
            elif fed_funds > core_pce + 1.0:
                regime = "TIGHTENING"
            elif fed_funds < core_pce:
                regime = "EASING"
            else:
                regime = "STABLE"

            return {
                "status": "SUCCESS",
                "source": "FRED (Federal Reserve Economic Data)",
                "as_of": datetime.now(timezone.utc).isoformat(),
                "indicators": indicators,
                "macro_regime_assessment": regime,
                "interpretation_note": (
                    "Yield spread > 0 = normal curve. "
                    "Fed funds > core PCE = restrictive policy. "
                    "Unemployment < 4.5% = tight labor market."
                )
            }

        except Exception as e:
            logger.error(f"Error consultando FRED API: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": f"FRED_API_ERROR: {str(e)}"
            }

# Instancia singleton y función helper a nivel de módulo
_fred_singleton = FREDTool()

def get_macro_indicators(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Helper funcional para invocar FRED con singleton o api_key dedicada."""
    if api_key:
        return FREDTool(api_key=api_key).get_macro_indicators()
    return _fred_singleton.get_macro_indicators()
