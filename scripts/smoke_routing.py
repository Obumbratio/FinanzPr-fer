"""
Smoke test: verifica que el clasificador de intención y el routing de 3 tiers funcionen correctamente.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src.agent.fast_chat import classify_query

test_cases = [
    # (input, expected_tier, description)
    ("$NVDA", "ultra", "Ticker explicito con $ -> Ultra"),
    ("Audita el riesgo de $TSLA", "ultra", "Auditoria explicita -> Ultra"),
    ("Dame un análisis completo de NVDA", "ultra", "Analisis completo + ticker -> Ultra"),
    ("Hazme un due diligence de AAPL", "ultra", "Due diligence + ticker -> Ultra"),
    ("NVDA insider form 4", "ultra", "Ticker + termino forense -> Ultra"),

    ("Analiza MSFT", "super", "Ticker sin $ con termino medio -> Super"),
    ("Cuál es el pronóstico de AMD", "super", "Pronostico + ticker -> Super"),
    ("Riesgo de Tesla", "super", "Termino medio + empresa -> Super o Ultra"),
    ("PLTR earnings", "super", "Ticker + earnings -> Super"),

    ("¿Qué es el ratio P/E?", "nano", "Pregunta educativa -> Nano"),
    ("Cómo estructuro una cartera con $5000", "nano", "Planificacion personal -> Nano"),
    ("Explícame qué es un put spread", "nano", "Educacion -> Nano"),
    ("¿Qué es la diversificación?", "nano", "Concepto teorico -> Nano"),
    ("Hola, buenas tardes", "nano", "Saludo -> Nano"),
]

print("=" * 70)
print("VERIFICACION DEL CLASIFICADOR DE INTENCION (3 TIERS)")
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
    icon = "[OK]  " if status == "OK" else "[FAIL]"
    print(f"  {icon} [{result:5s}] {desc}")
    if status == "FAIL":
        print(f"         EXPECTED: {expected}, GOT: {result}")
        print(f"         INPUT: \"{query}\"")

print(f"\n{'=' * 70}")
print(f"RESULTADO: {passed}/{len(test_cases)} pasaron, {failed} fallaron.")
if failed == 0:
    print("CLASIFICADOR VERIFICADO CON EXITO.")
else:
    print(f"ATENCION: {failed} casos necesitan ajuste.")
print(f"{'=' * 70}")

if failed > 0:
    sys.exit(1)
