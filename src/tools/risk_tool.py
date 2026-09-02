import math
from typing import Dict, Any

class RiskEngineTool:
    """
    Motor heurístico de evaluación de riesgo y régimen de volatilidad.
    Proporciona un Risk Score determinista para auditorías financieras.
    """
    def evaluate_risk(self, ticker: str, volatility_window: int = 14) -> Dict[str, Any]:
        ticker = ticker.upper()
        
        # Mapeo determinista de regímenes base para auditoría de ejemplo
        tech_symbols = ["NVDA", "TSLA", "AMD", "PLTR", "META"]
        stable_symbols = ["AAPL", "MSFT", "GOOGL", "JPM", "KO"]
        
        if ticker in tech_symbols:
            base_volatility = 0.38
            regime = "ELEVATED_VOLATILITY"
            short_interest_pct = 4.2
            insider_signal = "BEARISH_DIVERGENCE"
        elif ticker in stable_symbols:
            base_volatility = 0.18
            regime = "STABLE_ACCUMULATION"
            short_interest_pct = 1.1
            insider_signal = "NEUTRAL"
        else:
            base_volatility = 0.25
            regime = "NORMAL_REGIME"
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
            "annualized_volatility_est": f"{base_volatility * 100:.1f}%",
            "short_interest_est": f"{short_interest_pct}%",
            "insider_alignment": insider_signal,
            "disclaimer": "Educational audit heuristic — Not financial advice."
        }
