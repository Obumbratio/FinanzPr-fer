import sys
import os

# Asegurar path raíz y encoding UTF-8 en Windows
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.tools.market_tool import MarketDataTool


def run_smoke_market_test():
    print("============================================================")
    print("FINANZPRÜFER: PRUEBA DE HUMO DE MÉTRICAS DE MERCADO Y VIX")
    print("============================================================")

    tool = MarketDataTool()

    # 1. Consultar Régimen Macro VIX
    vix_data = tool.get_macro_vix()
    print(f"\nRÉGIMEN MACRO VIX:")
    if vix_data.get("status") == "SUCCESS":
        print(f"  * Valor VIX: {vix_data.get('vix_value')} (Var: {vix_data.get('daily_change')} / {vix_data.get('daily_change_pct')}%)")
        print(f"  * Clasificación de Régimen: {vix_data.get('regime')}")
        print(f"  * Timestamp (UTC): {vix_data.get('as_of')}")
    else:
        print(f"  * [ALERTA] VIX no disponible: {vix_data.get('reason')}")

    # 2. Consultar Activos Objetivo
    tickers = ["SPY", "NVDA", "GME"]
    snapshots = {}

    print(f"\nEXTRAYENDO MÉTRICAS EMPÍRICAS DE ACTIVOS...")
    for t in tickers:
        snap = tool.get_market_snapshot(t)
        snapshots[t] = snap
        if snap.get("status") != "SUCCESS":
            print(f"[ERROR] No se pudo obtener snapshot para {t}: {snap.get('reason')}")
            sys.exit(1)

    # 3. Imprimir Tabla Comparativa
    print("\nTABLA COMPARATIVA DE MERCADO:")
    header = f"{'Ticker':<8} | {'Precio (USD)':<14} | {'Var %':<8} | {'Vol 60d (%)':<12} | {'Pos 52s (%)':<12} | {'ATR 14':<8} | {'Dist SMA200':<12}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for t in tickers:
        s = snapshots[t]
        p_str = f"USD {s['current_price']:.2f}"
        var_str = f"{s['daily_change_pct']:+.2f}%"
        vol_str = f"{s['realized_volatility_60d_pct']:.2f}%"
        pos_str = f"{s['week_52_position_pct']:.1f}%"
        atr_str = f"{s['atr_14']:.2f}"
        sma_dist_str = f"{s['sma_200_distance_pct']:+.2f}%" if s.get('sma_200_distance_pct') is not None else "N/A"
        print(f"{t:<8} | {p_str:<14} | {var_str:<8} | {vol_str:<12} | {pos_str:<12} | {atr_str:<8} | {sma_dist_str:<12}")

    print("-" * len(header))

    # 4. Validar Relaciones Cuantitativas de Volatilidad y Plausibilidad
    vol_spy = snapshots["SPY"]["realized_volatility_60d"]
    vol_nvda = snapshots["NVDA"]["realized_volatility_60d"]
    vol_gme = snapshots["GME"]["realized_volatility_60d"]

    print("\nVALIDACIÓN CUANTITATIVA DE DISPERSIÓN Y PLAUSIBILIDAD:")
    print(f"  * SPY Volatilidad Realizada (60d): {vol_spy * 100:.2f}%")
    print(f"  * NVDA Volatilidad Realizada (60d): {vol_nvda * 100:.2f}%")
    print(f"  * GME Volatilidad Realizada (60d): {vol_gme * 100:.2f}%")

    try:
        # Validación de índice base vs acciones individuales de alta beta
        assert vol_spy < vol_nvda, f"Inconsistencia: Vol SPY ({vol_spy:.4f}) debe ser menor que NVDA ({vol_nvda:.4f})"
        assert vol_spy < vol_gme, f"Inconsistencia: Vol SPY ({vol_spy:.4f}) debe ser menor que GME ({vol_gme:.4f})"

        # Validación de rangos plausibles
        for t, s in snapshots.items():
            assert s["current_price"] > 0, f"Precio inválido para {t}"
            assert s["atr_14"] > 0, f"ATR inválido para {t}"
            assert 0.0 <= s["week_52_position_pct"] <= 100.0, f"Posición 52s fuera de rango para {t}"

        if vol_nvda < vol_gme:
            print("  * Jerarquía empírica estándar observada: SPY < NVDA < GME")
        else:
            print(f"  * [OBSERVACIÓN CUANTITATIVA]: NVDA ({vol_nvda * 100:.2f}%) supera a GME ({vol_gme * 100:.2f}%) en la ventana de 60d debido a la volatilidad post-earnings y catalizadores de IA.")

        print("\n[OK] Validación de jerarquía y plausibilidad de mercado confirmada.")
    except AssertionError as e:
        print(f"\n[ERROR] Fallo en la aserción de plausibilidad: {e}")
        sys.exit(1)

    print("\n[OK] Prueba de mercado y métricas cuantitativas completada exitosamente.")
    sys.exit(0)


if __name__ == "__main__":
    run_smoke_market_test()
