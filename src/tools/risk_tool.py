import logging
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import numpy as np
import yfinance as yf

from src.tools.market_tool import MarketDataTool
from src.tools.sec_tool import SECTool

logger = logging.getLogger(__name__)


def _norm_cdf(x: float) -> float:
    """Distribución normal acumulada estándar exacta vía función error erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


class RiskEngineTool:
    """
    Motor cuantitativo empírico de evaluación de riesgo forense y escenarios a 12 meses.
    Integra series temporales reales, correlación empírica rho contra SPY, volatilidad a 90d,
    y señales forenses de alineación insider desde SEC Form 4 (5 factores ponderados).
    """

    def __init__(
        self,
        market_tool: Optional[MarketDataTool] = None,
        sec_tool: Optional[SECTool] = None
    ):
        self.market_tool = market_tool or MarketDataTool()
        self.sec_tool = sec_tool or SECTool()

    def evaluate_risk(self, ticker: str) -> Dict[str, Any]:
        """
        Calcula el Composite Risk Score de 5 factores (0-100), correlación rho empírica vs SPY,
        varianza de spread, escenarios log-normales a 12 meses (90d vol) y probabilidad de outperformance a 3M.
        """
        clean_ticker = ticker.replace("$", "").strip().upper()
        as_of = datetime.now(timezone.utc).isoformat()

        if not clean_ticker:
            return {
                "status": "UNAVAILABLE",
                "reason": "EMPTY_TICKER",
                "ticker": clean_ticker,
                "as_of": as_of
            }

        try:
            # 1. Invocar las herramientas de mercado y SEC
            market_data = self.market_tool.get_market_snapshot(clean_ticker)
            spy_data = self.market_tool.get_market_snapshot("SPY")
            vix_snap = self.market_tool.get_macro_vix()
            insider_data = self.sec_tool.get_insider_trades(clean_ticker)

            if market_data.get("status") != "SUCCESS":
                return {
                    "status": "UNAVAILABLE",
                    "reason": "MARKET_DATA_FAILED",
                    "ticker": clean_ticker,
                    "as_of": as_of,
                    "error_details": market_data.get("reason")
                }

            if spy_data.get("status") != "SUCCESS":
                return {
                    "status": "UNAVAILABLE",
                    "reason": "SPY_BENCHMARK_DATA_FAILED",
                    "ticker": clean_ticker,
                    "as_of": as_of,
                    "error_details": spy_data.get("reason")
                }

            # 2. Descargar retornos diarios de 6 meses para alinear y extraer últimos 90 días
            hist_asset_df = yf.download(clean_ticker, period="6mo", interval="1d", progress=False)
            hist_spy_df = yf.download("SPY", period="6mo", interval="1d", progress=False)

            if hist_asset_df.empty or hist_spy_df.empty:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "HISTORICAL_RETURNS_UNAVAILABLE",
                    "ticker": clean_ticker,
                    "as_of": as_of
                }

            close_asset = hist_asset_df["Close"].squeeze()
            close_spy = hist_spy_df["Close"].squeeze()

            ret_asset = close_asset.pct_change().dropna()
            ret_spy = close_spy.pct_change().dropna()

            aligned = ret_asset.align(ret_spy, join="inner")
            aligned_asset = aligned[0].tail(90)
            aligned_spy = aligned[1].tail(90)

            returns_asset = aligned_asset.values.astype(float)
            returns_spy = aligned_spy.values.astype(float)

            # Correlación empírica rho de Pearson
            if len(returns_asset) >= 5 and len(returns_spy) >= 5:
                if clean_ticker == "SPY":
                    rho = 1.0
                else:
                    corr_matrix = np.corrcoef(returns_asset, returns_spy)
                    rho_val = float(corr_matrix[0, 1])
                    rho = rho_val if not np.isnan(rho_val) else 0.5
            else:
                rho = 1.0 if clean_ticker == "SPY" else 0.5

            # 3. Volatilidades realizadas anualizadas a 90 días (proxy forward empírico)
            if len(returns_asset) >= 5:
                sigma_a = float(np.std(returns_asset, ddof=1) * np.sqrt(252))
            else:
                sigma_a = float(market_data.get("realized_volatility_60d", 0.25))

            if len(returns_spy) >= 5:
                sigma_spy = float(np.std(returns_spy, ddof=1) * np.sqrt(252))
            else:
                sigma_spy = float(spy_data.get("realized_volatility_60d", 0.15))

            vol_90d = max(sigma_a, 0.01)

            # 4. Varianza del spread y probabilidad de outperformance a 3M (t = 0.25)
            var_spread = (sigma_a ** 2) + (sigma_spy ** 2) - (2.0 * rho * sigma_a * sigma_spy)
            sigma_spread = math.sqrt(max(var_spread, 1e-10))

            r_a = float(returns_asset.sum())
            r_spy = float(returns_spy.sum())

            t_spread = 0.25  # 3 meses
            if sigma_spread > 1e-6 and clean_ticker != "SPY":
                z = (r_a - r_spy) / (sigma_spread * math.sqrt(t_spread))
                prob_outperformance = _norm_cdf(z)
            else:
                prob_outperformance = 0.5

            prob_outperformance = min(max(prob_outperformance, 0.01), 0.99)

            # 5. Escenarios Log-Normales a 12 Meses (t = 1.0 año, deriva cero mu=0)
            price = float(market_data.get("current_price") or market_data.get("price", 0.0))
            bear_case = round(price * math.exp(-vol_90d * math.sqrt(1.0)), 2)
            base_case = round(price, 2)
            bull_case = round(price * math.exp(+vol_90d * math.sqrt(1.0)), 2)

            # 6. Factor S_insider forense
            if insider_data.get("status") != "SUCCESS":
                s_insider = 50.0  # Neutral con penalización documentada
                alignment = "UNAVAILABLE"
            else:
                alignment = insider_data.get("summary", {}).get("insider_alignment", "NEUTRAL")
                if alignment == "BEARISH_DIVERGENCE":
                    s_insider = 85.0
                elif alignment == "BULLISH_ACCUMULATION":
                    s_insider = 20.0
                else:  # NEUTRAL
                    s_insider = 50.0

            # 7. Normalización de 5 Factores Cuantitativos (0 a 100)
            # Factor 1: Volatilidad realizada 90d (30% peso) - escala 0 a 75% vol
            s_vol = min(max((vol_90d / 0.75) * 100.0, 0.0), 100.0)

            # Factor 2: Rango en canal de 52 semanas (15% peso)
            week_52_pos_pct = float(market_data.get("week_52_position_pct", 50.0))
            s_range = min(max(week_52_pos_pct, 0.0), 100.0)

            # Factor 3: Distancia a la SMA 200 (15% peso) - tensión de reversión
            sma_200_dist_pct = float(market_data.get("sma_200_distance_pct") or 0.0)
            s_trend = min(max(50.0 + (sma_200_dist_pct * 1.5), 0.0), 100.0)

            # Factor 4: Régimen macro VIX (10% peso) - escala 10 a 35 VIX
            vix_value = float(vix_snap.get("vix_value", 18.0)) if vix_snap.get("status") == "SUCCESS" else 18.0
            macro_regime = vix_snap.get("regime", "NORMAL_REGIME") if vix_snap.get("status") == "SUCCESS" else "NORMAL_REGIME"
            s_vix = min(max(((vix_value - 10.0) / 25.0) * 100.0, 0.0), 100.0)

            # Factor 5: S_insider forense (30% peso)

            # Composite Risk Score de 5 Factores
            score = (0.30 * s_vol) + (0.15 * s_range) + (0.15 * s_trend) + (0.10 * s_vix) + (0.30 * s_insider)
            composite_risk_score = round(float(min(max(score, 0.0), 100.0)), 1)

            # Tiers normalizados
            if composite_risk_score >= 70.0:
                risk_tier = "CRITICAL"
            elif composite_risk_score >= 45.0:
                risk_tier = "MODERATE"
            else:
                risk_tier = "LOW"

            return {
                "status": "SUCCESS",
                "source": "empirical_risk_engine",
                "ticker": clean_ticker,
                "as_of": as_of,
                "current_price": price,
                "price": price,
                "composite_risk_score": composite_risk_score,
                "risk_tier": risk_tier,
                "macro_regime": macro_regime,
                "vix_value": round(vix_value, 2),
                "rho_correlation": round(rho, 4),
                "sigma_spy": round(sigma_spy, 4),
                "prob_outperformance_3m": round(prob_outperformance, 4),
                "outperform_prob_3m_pct": round(prob_outperformance * 100.0, 1),
                "insider_alignment": alignment,
                "insider_summary": insider_data.get("summary") if insider_data.get("status") == "SUCCESS" else None,
                "scenario_assumptions": "Zero drift (mu=0), realized vol 90d as forward proxy, Pearson rho from 90d daily returns",
                "metrics": {
                    "realized_vol_90d": round(vol_90d, 4),
                    "realized_vol_90d_pct": round(vol_90d * 100.0, 2),
                    "realized_volatility_60d": round(market_data.get("realized_volatility_60d", vol_90d), 4),
                    "realized_volatility_60d_pct": round(market_data.get("realized_volatility_60d_pct", vol_90d * 100.0), 2),
                    "week_52_position_pct": round(week_52_pos_pct, 2),
                    "sma_200_distance_pct": round(sma_200_dist_pct, 2),
                    "atr_14": market_data.get("atr_14", 0.0)
                },
                "factor_breakdown": {
                    "volatility_component": round(s_vol, 1),
                    "week_52_component": round(s_range, 1),
                    "sma200_component": round(s_trend, 1),
                    "vix_component": round(s_vix, 1),
                    "insider_component": round(s_insider, 1)
                },
                "scenarios_12m": {
                    "bear_case": bear_case,
                    "base_case": base_case,
                    "bull_case": bull_case
                },
                "disclaimer": "Educational quantitative risk engine — Not financial advice."
            }

        except Exception as e:
            logger.error(f"Error evaluando riesgo cuantitativo para {clean_ticker}: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": str(e),
                "ticker": clean_ticker,
                "as_of": as_of
            }
