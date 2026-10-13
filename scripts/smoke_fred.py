"""Smoke test for FRED macro indicators."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.fred_tool import get_macro_indicators

# Asegurar codificación UTF-8 en Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=" * 60)
print("INDICADORES MACROECONÓMICOS (FRED)")
print("=" * 60)

result = get_macro_indicators()
print(f"  Status: {result['status']}")

if result["status"] == "SUCCESS":
    indicators = result["indicators"]
    for name, data in indicators.items():
        if isinstance(data, dict):
            print(f"  {name}: {data.get('value', 'N/A')} ({data.get('date', 'N/A')})")
        else:
            print(f"  {name}: {data}")
    print(f"\n  Macro Regime: {result.get('macro_regime_assessment', 'N/A')}")
    
    # Asserts
    assert indicators.get("treasury_10y", {}).get("value", 0) > 0, "Treasury 10Y should be positive"
    assert indicators.get("unemployment", {}).get("value", 0) > 0, "Unemployment should be positive"
    print("\n  ✓ [OK] FRED macro indicators verified.")
elif result["status"] == "UNAVAILABLE":
    print(f"  Reason: {result.get('reason', 'Unknown')}")
    print("  * [SKIP] FRED not configured — this is optional.")
else:
    print("  ✗ [FAIL] Unexpected status.")

print("=" * 60)
