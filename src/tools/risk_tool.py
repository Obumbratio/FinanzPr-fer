import math
from typing import Dict, Any

class RiskEngineTool:
    """
    Motor heurístico de evaluación de riesgo y régimen de volatilidad (Börsenhirn Pattern).
    Proporciona un Risk Score determinista y clasificación de régimen macro de 4 estados.
    """

    @staticmethod
    def get_macro_market_regime(vix_estimate: float = 16.4) -> Dict[str, Any]:
        """
        Calcula el régimen macroeconómico global derivado de Börsenhirn:
        Estados posibles:
          - PANIC (VIX >= 30.0): Estrés de liquidez extremo y ventas forzadas.
          - BEAR (20.0 <= VIX < 30.0): Distribución y aversión al riesgo elevada.
          - SIDEWAYS (15.0 <= VIX < 20.0): Rango lateral y rotación sectorial selectiva.
          - BULL (VIX < 15.0): Expansión, complacencia y acumulación de activos de riesgo.
        """
        if vix_estimate >= 30.0:
            regime = "PANIC"
            desc = "Extreme liquidity stress, systemic deleveraging and forced liquidations."
            posture = "CAPITAL_PRESERVATION"
        elif vix_estimate >= 20.0:
            regime = "BEAR"
            desc = "Elevated risk aversion, institutional distribution and volatility spikes."
            posture = "DEFENSIVE_HEDGING"
        elif vix_estimate >= 15.0:
            regime = "SIDEWAYS"
            desc = "Selective tech rotation, moderate risk appetite and range-bound trading."
            posture = "TACTICAL_SELECTIVITY"
        else:
            regime = "BULL"
            desc = "Risk-on expansion, high market breadth and stable accumulation."
            posture = "AGGRESSIVE_GROWTH"

        return {
            "vix_estimate": vix_estimate,
            "regime": regime,
            "description": desc,
            "recommended_posture": posture,
            "disclaimer": "Educational heuristic model — Not financial advice."
        }

    def evaluate_risk(self, ticker: str, volatility_window: int = 14) -> Dict[str, Any]:
        ticker = ticker.upper()
        
        # Mapeo determinista de regímenes base para auditoría institucional
        tech_high_beta = ["NVDA", "TSLA", "AMD", "PLTR", "META", "COIN"]
        stable_mega_caps = ["AAPL", "MSFT", "GOOGL", "JPM", "KO", "BRK.B", "SPY", "QQQ", "DIA", "IWM"]
        
        if ticker in tech_high_beta:
            base_volatility = 0.38
            regime = "ELEVATED_VOLATILITY"
            macro_state = "SIDEWAYS / HIGH_BETA_EXPANSION"
            short_interest_pct = 4.2
            insider_signal = "BEARISH_DIVERGENCE"
        elif ticker in stable_mega_caps:
            base_volatility = 0.18
            regime = "STABLE_ACCUMULATION"
            macro_state = "BULL_ACCUMULATION"
            short_interest_pct = 1.1
            insider_signal = "NEUTRAL"
        else:
            base_volatility = 0.25
            regime = "NORMAL_REGIME"
            macro_state = "SIDEWAYS_EQUILIBRIUM"
            short_interest_pct = 2.5
            insider_signal = "BALANCED"

        # Cálculo de Risk Score (0-100)
        # Ingredientes: Volatilidad (40%), Short Interest (30%), Presión Heurística (30%)
        vol_score = min(base_volatility * 100 * 1.5, 40.0)
        short_score = min(short_interest_pct * 7.5, 30.0)
        heuristic_penalty = 20.0 if insider_signal == "BEARISH_DIVERGENCE" else 10.0
        
        composite_risk_score = round(vol_score + short_score + heuristic_penalty, 1)

        # Clasificación del nivel de riesgo
        if composite_risk_score >= 70:
            risk_tier = "CRITICAL / HIGH RISK"
        elif composite_risk_score >= 45:
            risk_tier = "MODERATE RISK"
        else:
            risk_tier = "LOW / CONTROLLED RISK"

        return {
            "ticker": ticker,
            "composite_risk_score": composite_risk_score,
            "risk_tier": risk_tier,
            "regime": regime,
            "macro_state": macro_state,
            "annualized_volatility_est": f"{base_volatility * 100:.1f}%",
            "short_interest_est": f"{short_interest_pct}%",
            "insider_alignment": insider_signal,
            "disclaimer": "Educational audit heuristic — Not financial advice."
        }
