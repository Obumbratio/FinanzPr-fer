"""Extended routing test with market overview and planning queries."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.fast_chat import classify_query

# Asegurar codificación UTF-8 en Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

test_cases = [
    # Existing cases (must still pass)
    ("$NVDA", "ultra", "Ticker explícito con $ → Ultra"),
    ("Dame un análisis completo de NVDA", "ultra", "Análisis completo + ticker → Ultra"),
    ("Analiza MSFT", "super", "Ticker sin $ con término medio → Super"),
    ("¿Qué es el ratio P/E?", "nano", "Pregunta educativa → Nano"),
    ("Hola, buenas tardes", "nano", "Saludo → Nano"),
    
    # NEW: Market overview queries → Ultra
    ("Dame un análisis del mercado", "ultra", "Market overview → Ultra"),
    ("¿Cómo va el mercado americano?", "ultra", "Mercado americano → Ultra"),
    ("Market overview", "ultra", "English market overview → Ultra"),
    ("Panorama macro", "ultra", "Macro panorama → Ultra"),
    ("¿Cómo va Wall Street?", "ultra", "Wall Street → Ultra"),
    
    # NEW: Personal planning → Nano (NOT "sin respuesta")
    ("Tengo 2 mil dólares, ¿dónde invierto?", "nano", "Planificación personal → Nano"),
    ("Cómo estructuro una cartera con $5000", "nano", "Planificación personal → Nano"),
    ("¿Debería abrir un Roth IRA?", "nano", "Pregunta de finanzas personales → Nano"),
    ("Tengo deuda de tarjeta, ¿qué hago primero?", "nano", "Deuda personal → Nano"),
]

print("=" * 70)
print("VERIFICACIÓN EXTENDIDA DEL CLASIFICADOR (3 TIERS + MARKET OVERVIEW)")
print("=" * 70)

passed = 0
failed = 0
for query, expected, desc in test_cases:
    result = classify_query(query)
    status = "OK" if result == expected else "FAIL"
    if status == "OK":
        passed += 1
    else:
        failed += 1
    icon = "✓" if status == "OK" else "✗"
    print(f"  {icon} [{result:5s}] {desc}")
    if status == "FAIL":
        print(f"      EXPECTED: {expected}, GOT: {result}")
        print(f"      INPUT: \"{query}\"")

print(f"\n{'=' * 70}")
print(f"RESULTADO: {passed}/{len(test_cases)} pasaron, {failed} fallaron.")
if failed == 0:
    print("CLASIFICADOR EXTENDIDO VERIFICADO CON ÉXITO.")
else:
    print(f"ATENCIÓN: {failed} casos necesitan ajuste.")
print(f"{'=' * 70}")

assert failed == 0, f"{failed} test cases failed in classify_query"
