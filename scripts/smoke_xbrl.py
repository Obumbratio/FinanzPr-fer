"""
Smoke test: verifica que get_fundamentals devuelve datos XBRL reales de SEC EDGAR.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.tools.xbrl_tool import get_fundamentals

for ticker in ["NVDA", "TSLA", "AAPL"]:
    print(f"\n{'='*60}")
    print(f"FUNDAMENTALES XBRL: ${ticker}")
    print(f"{'='*60}")
    
    result = get_fundamentals(ticker)
    print(f"  Status: {result['status']}")
    
    if result["status"] in ("SUCCESS", "PARTIAL"):
        period = result.get("period", {})
        print(f"  Período: {period.get('end_date', 'N/A')} ({period.get('form', 'N/A')})")
        
        print(f"\n  Valores crudos:")
        for key, val_info in result.get("raw_values", {}).items():
            if val_info and val_info.get("value") is not None:
                v = val_info["value"]
                if abs(v) > 1_000_000:
                    print(f"    {key}: ${v/1e9:.2f}B ({val_info.get('end', 'N/A')})")
                else:
                    print(f"    {key}: ${v:,.0f} ({val_info.get('end', 'N/A')})")
            else:
                print(f"    {key}: UNAVAILABLE")
        
        print(f"\n  Métricas derivadas:")
        derived = result.get("derived_metrics", {})
        if derived.get("ocf_ni_ratio") is not None:
            print(f"    OCF/NI Ratio: {derived['ocf_ni_ratio']:.2f}")
        else:
            print(f"    OCF/NI Ratio: UNAVAILABLE")
        if derived.get("dso_days") is not None:
            print(f"    DSO (días): {derived['dso_days']:.1f}")
        else:
            print(f"    DSO: UNAVAILABLE")
        if derived.get("dio_days") is not None:
            print(f"    DIO (días): {derived['dio_days']:.1f}")
        else:
            print(f"    DIO: UNAVAILABLE")
        if derived.get("net_debt_usd") is not None:
            nd = derived["net_debt_usd"]
            label = "CASH RICH" if nd < 0 else "LEVERAGED"
            print(f"    Deuda Neta: ${nd/1e9:.2f}B ({label})")
        else:
            print(f"    Deuda Neta: UNAVAILABLE")
        if derived.get("gross_margin") is not None:
            print(f"    Margen Bruto: {derived['gross_margin']*100:.1f}%")
        else:
            print(f"    Margen Bruto: UNAVAILABLE")
        
        interp = result.get("interpretation", {})
        print(f"\n  Interpretación:")
        print(f"    Calidad de earnings: {interp.get('ocf_ni_ratio', 'N/A')}")
        print(f"    Posición de deuda: {interp.get('net_debt', 'N/A')}")
        
        unavailable = result.get("concepts_unavailable", [])
        if unavailable:
            print(f"\n  Conceptos no disponibles: {', '.join(unavailable)}")
        
        # Asserts básicos
        assert result["raw_values"].get("revenue") is not None or result["raw_values"].get("net_income") is not None, \
            f"Al menos revenue o net_income debe estar disponible para {ticker}"
        
        print(f"\n  * [OK] ${ticker}: Fundamentales verificados.")
    else:
        print(f"  Razón: {result.get('reason', 'Unknown')}")
        print(f"  * [WARN] ${ticker}: Fundamentales no disponibles.")

print(f"\n{'='*60}")
print("VERIFICACIÓN DE FUNDAMENTALES XBRL COMPLETADA.")
print(f"{'='*60}")
