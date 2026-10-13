import sys
import os

# Asegurar path raíz y encoding UTF-8 en Windows
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.tools.sec_tool import SECTool


def run_smoke_sec_xml():
    print("=" * 105)
    print("FINANZPRÜFER: SMOKE TEST FORENSE — PARSER XML SEC EDGAR (FORM 4 REAL)")
    print("=" * 105)

    sec_tool = SECTool()
    tickers = ["NVDA", "TSLA"]
    results = {}

    print("\n[1/3] DESCARGANDO Y PARSEANDO FORM 4 XML EN TIEMPO REAL DESDE SEC EDGAR...")
    for t in tickers:
        print(f"  -> Consultando filings recientes y descargando XMLs para ${t}...")
        res = sec_tool.get_insider_trades(t, max_filings=5)
        results[t] = res
        if res.get("status") != "SUCCESS":
            print(f"[ERROR CRÍTICO] Fallo en la recuperación de Form 4 para {t}: {res.get('reason')} - {res.get('message')}")
            sys.exit(1)

    # 1. Tabla Formateada Consolidada
    print("\n" + "=" * 105)
    print("RESUMEN CONSOLIDADO DE ACTIVIDAD INSIDER (ÚLTIMOS FILINGS FORM 4)")
    print("=" * 105)
    header = (
        f"{'Ticker':<6} | {'CIK':<10} | {'Total Comprado (P)':<20} | {'Ventas Discrecionales':<22} | "
        f"{'Ventas 10b5-1':<16} | {'Flujo Neto Discrecional':<24} | {'Alineación'}"
    )
    print(header)
    print("-" * 105)

    for t in tickers:
        r = results[t]
        s = r["summary"]
        cik = sec_tool._get_cik(t)
        p_str = f"USD {s['total_bought_usd']:,.2f}"
        disc_str = f"USD {s['discretionary_sold_usd']:,.2f}"
        prog_str = f"USD {s['programmed_10b51_sold_usd']:,.2f}"
        net_str = f"USD {s['net_discretionary_flow_usd']:,.2f}"
        align_str = s["insider_alignment"]
        print(f"{t:<6} | {cik:<10} | {p_str:<20} | {disc_str:<22} | {prog_str:<16} | {net_str:<24} | {align_str}")

    print("-" * 105)

    # 2. Primeras 5 Transacciones Individuales por Ticker
    print("\n[2/3] DETALLE DE LAS PRIMERAS 5 TRANSACCIONES INDIVIDUALES PARSEADAS:")
    for t in tickers:
        trades = results[t].get("trades", [])
        print(f"\n  DETALLE ${t} (Total transacciones: {len(trades)}, Filings: {results[t]['summary']['filings_parsed']}):")
        tx_header = f"    {'Fecha':<10} | {'Reportante':<26} | {'Código':<6} | {'Acciones':<12} | {'Precio':<10} | {'Total USD':<16} | {'10b5-1 Plan'}"
        print(tx_header)
        print("    " + "-" * 98)

        for tx in trades[:5]:
            filer = (tx["filer"][:24] + "..") if len(tx["filer"]) > 26 else tx["filer"]
            shares_str = f"{tx['shares']:,.2f}"
            price_str = f"USD {tx['price_per_share']:.2f}"
            tot_str = f"USD {tx['total_usd']:,.2f}"
            plan_str = "SÍ (Rule 10b5-1)" if tx["is_10b51"] is True else ("NO (Discretionary)" if tx["is_10b51"] is False else "Indeterminado")
            print(f"    {tx['date']:<10} | {filer:<26} | {tx['code']:<6} | {shares_str:<12} | {price_str:<10} | {tot_str:<16} | {plan_str}")

    # 3. Aserciones y Validaciones Estrictas
    print("\n[3/3] EJECUTANDO ASERCIONES Y VALIDACIONES ESTRUCTURALES...")
    for t in tickers:
        res = results[t]
        # A. status == "SUCCESS"
        assert res.get("status") == "SUCCESS", f"Fallo: status no es SUCCESS para {t}: {res.get('status')}"
        
        # B. len(trades) >= 1
        trades = res.get("trades", [])
        assert len(trades) >= 1, f"Fallo: len(trades) < 1 para {t} (encontrados: {len(trades)})"

        # C. Cada trade tiene "code", "shares" con valor numérico
        for idx, tr in enumerate(trades):
            assert "code" in tr and isinstance(tr["code"], str), f"Trade {idx} de {t} sin campo code válido: {tr}"
            assert "shares" in tr and isinstance(tr["shares"], (int, float)), f"Trade {idx} de {t} sin shares numérico: {tr}"

        # D. insider_alignment está en enum permitido
        alignment = res["summary"]["insider_alignment"]
        allowed_alignments = ["BEARISH_DIVERGENCE", "BULLISH_ACCUMULATION", "NEUTRAL"]
        assert alignment in allowed_alignments, f"Alineación inválida para {t}: '{alignment}' no en {allowed_alignments}"

        print(f"  * [OK] ${t}: Validado exitosamente ({len(trades)} transacciones, señal: {alignment}).")

    print("\n" + "=" * 105)
    print("VERIFICACIÓN SEC FORM 4 XML COMPLETADA: 100% DATOS REALES DE EDGAR, CERO SINTÉTICOS.")
    print("=" * 105)
    sys.exit(0)


if __name__ == "__main__":
    run_smoke_sec_xml()
