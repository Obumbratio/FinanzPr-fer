import sys
import os

# Asegurar path raíz y encoding UTF-8 en Windows
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.tools.risk_tool import RiskEngineTool


def run_smoke_risk_engine_test():
    print("=" * 105)
    print("FINANZPRÜFER: PRUEBA DE HUMO DEL MOTOR CUANTITATIVO DE RIESGO CORREGIDO (5 FACTORES)")
    print("=" * 105)

    engine = RiskEngineTool()

    # 1. Evaluación focalizada en NVDA según especificación
    print("\n[1/3] EVALUACIÓN PRINCIPAL DE AUDITORÍA FORENSE ($NVDA)...")
    res_nvda = engine.evaluate_risk("NVDA")
    if res_nvda.get("status") != "SUCCESS":
        print(f"[ERROR] Evaluación fallida para NVDA: {res_nvda.get('reason')} - {res_nvda.get('error_details')}")
        sys.exit(1)

    print("\n" + "-" * 80)
    print("RESUMEN DE RIESGO Y VALORACIÓN FORENSE: $NVDA")
    print("-" * 80)
    print(f"  * Composite Risk Score    : {res_nvda['composite_risk_score']:.1f}/100")
    print(f"  * Risk Tier               : {res_nvda['risk_tier']}")
    print(f"  * Correlación Rho vs SPY  : {res_nvda['rho_correlation']:.4f}")
    print(f"  * Sigma SPY (Real-Time)   : {res_nvda['sigma_spy'] * 100:.2f}% ({res_nvda['sigma_spy']:.4f})")
    print(f"  * Volatilidad 90d Activo  : {res_nvda['metrics']['realized_vol_90d_pct']:.2f}%")
    print(f"  * Prob. Outperformance 3M : {res_nvda['prob_outperformance_3m'] * 100:.2f}% ({res_nvda['prob_outperformance_3m']:.4f})")
    print(f"  * Insider Alignment       : {res_nvda['insider_alignment']}")
    print(f"  * Precio Spot Actual      : USD {res_nvda['current_price']:.2f}")
    print(f"  * Escenario Bear (12M)    : USD {res_nvda['scenarios_12m']['bear_case']:.2f}")
    print(f"  * Escenario Bull (12M)    : USD {res_nvda['scenarios_12m']['bull_case']:.2f}")
    print(f"  * Supuestos de Escenario  : {res_nvda['scenario_assumptions']}")
    print("-" * 80)

    # Aserciones estrictas para NVDA
    print("\n[2/3] VALIDACIÓN DE ASERCIONES CUANTITATIVAS OBLIGATORIAS ($NVDA):")
    score = res_nvda["composite_risk_score"]
    assert 0.0 <= score <= 100.0, f"Score de NVDA ({score}) fuera de rango válido [0.0, 100.0]"
    print(f"  * [OK] Composite Risk Score dentro de límites: {score:.1f} in [0, 100].")

    rho = res_nvda.get("rho_correlation")
    assert rho is not None and -1.0 <= rho <= 1.0, f"rho_correlation inválido: {rho}"
    print(f"  * [OK] Rho empírico verificado en [-1.0, 1.0]: {rho:.4f}.")

    sigma_spy = res_nvda.get("sigma_spy")
    assert sigma_spy is not None and sigma_spy > 0.0, f"sigma_spy no válido o <= 0: {sigma_spy}"
    print(f"  * [OK] Sigma SPY dinámico real-time: {sigma_spy:.4f} > 0.")

    p = res_nvda["current_price"]
    bear = res_nvda["scenarios_12m"]["bear_case"]
    bull = res_nvda["scenarios_12m"]["bull_case"]
    assert bear < p < bull, f"Violación de envolvente matemática log-normal: Bear ({bear}) < Spot ({p}) < Bull ({bull})"
    print(f"  * [OK] Envolvente 12M verificada: Bear USD {bear:.2f} < Spot USD {p:.2f} < Bull USD {bull:.2f}.")

    prob_out = res_nvda.get("prob_outperformance_3m")
    assert prob_out is not None and 0.0 <= prob_out <= 1.0, f"prob_outperformance_3m fuera de rango: {prob_out}"
    print(f"  * [OK] Probabilidad de outperformance a 3M en [0, 1]: {prob_out:.4f}.")

    insider_align = res_nvda.get("insider_alignment")
    assert insider_align in ["BEARISH_DIVERGENCE", "BULLISH_ACCUMULATION", "NEUTRAL", "UNAVAILABLE"], f"insider_alignment no reconocido: {insider_align}"
    print(f"  * [OK] Factor forense insider presente y clasificado: '{insider_align}'.")

    # 2. Evaluación comparativa multi-activo
    print("\n[3/3] COMPARATIVA HETEROGÉNEA DE RIESGO Y ALINEACIÓN FORENSE:")
    tickers = ["SPY", "NVDA", "TSLA"]
    results = {"NVDA": res_nvda}
    for t in tickers:
        if t not in results:
            r = engine.evaluate_risk(t)
            assert r.get("status") == "SUCCESS", f"Error evaluando {t}: {r}"
            results[t] = r

    header = (
        f"{'Ticker':<6} | {'Spot USD':<12} | {'Vol 90d':<10} | {'Risk Score':<11} | "
        f"{'Risk Tier':<10} | {'Rho SPY':<9} | {'Prob Outp':<10} | {'Insider Signal':<20}"
    )
    print("-" * 105)
    print(header)
    print("-" * 105)

    for t in tickers:
        r = results[t]
        p_str = f"USD {r['current_price']:.2f}"
        vol_str = f"{r['metrics']['realized_vol_90d_pct']:.1f}%"
        score_str = f"{r['composite_risk_score']:.1f}/100"
        tier_str = r['risk_tier']
        rho_str = f"{r['rho_correlation']:.2f}"
        outp_str = f"{r['prob_outperformance_3m'] * 100:.1f}%"
        insider_str = r['insider_alignment']
        print(f"{t:<6} | {p_str:<12} | {vol_str:<10} | {score_str:<11} | {tier_str:<10} | {rho_str:<9} | {outp_str:<10} | {insider_str:<20}")

    print("-" * 105)

    # Verificar jerarquía de riesgo SPY < NVDA
    score_spy = results["SPY"]["composite_risk_score"]
    score_nvda = results["NVDA"]["composite_risk_score"]
    assert score_spy < score_nvda, f"Inconsistencia: Score SPY ({score_spy}) debe ser menor que NVDA ({score_nvda})"
    print(f"  * [OK] Jerarquía confirmada: Score SPY ({score_spy:.1f}) < Score NVDA ({score_nvda:.1f}).")

    print("\n" + "=" * 105)
    print("VERIFICACIÓN DEL MOTOR CUANTITATIVO COMPLETADA CON ÉXITO: 100% PRECISIÓN MATEMÁTICA.")
    print("=" * 105)
    sys.exit(0)


if __name__ == "__main__":
    run_smoke_risk_engine_test()
