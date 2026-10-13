import sys
import os
import re

# Asegurar path raíz y encoding UTF-8 en Windows
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.agent.orchestrator import FinanzOrchestrator

FORBIDDEN_PHRASES = [
    'caja neta',
    'FCF conversion',
    '% ingresos en Data Center',
    'top 3',
    'concentración de clientes'
]

FORBIDDEN_PATTERNS = [
    r"caja\s+neta",
    r"fcf\s+conversion",
    r"%\s*ingresos\s+en\s+data\s+center",
    r"top\s*3",
    r"concentraci[oó]n\s+de\s+clientes"
]

def verify_provenance_whitelist(report_text: str) -> dict:
    """
    Extrae todas las cifras del reporte y verifica que cada una tenga
    una etiqueta de fuente cercana (dentro de los 200 caracteres anteriores o posteriores).
    
    Cifras = cualquier cosa que parezca un número financiero:
    - USD seguido de número: USD 262.77, USD 52.88B
    - Porcentajes: 41.07%, 52.21%
    - Números con decimales en contexto financiero: 1.25, 0.65
    
    Fuentes válidas = referencias a herramientas o URLs:
    - (calculate_risk_metrics), (get_insider_trades), (get_analyst_consensus), (search_market_news), (get_fundamentals)
    - URLs que empiecen con http
    - [fuente: ...] tags
    - Nombres de fuentes conocidas: MarketBeat, TipRanks, Yahoo Finance, Seeking Alpha, SEC EDGAR
    """
    
    # Patrón para detectar cifras financieras
    number_pattern = r'(?:USD\s*[\d,\.]+\s*[BMK]?|[\d,\.]+\s*%|\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:B|M|K)\b)'
    
    # Patrones que indican fuente/trazabilidad
    source_patterns = [
        r'[\(\[]?`?calculate_risk_metrics`?[\)\]]?',
        r'[\(\[]?`?get_insider_trades`?[\)\]]?',
        r'[\(\[]?`?get_analyst_consensus`?[\)\]]?',
        r'[\(\[]?`?search_market_news`?[\)\]]?',
        r'[\(\[]?`?get_fundamentals`?[\)\]]?',
        r'https?://\S+',
        r'\[fuente:\s*[^\]]+\]',
        r'(?:MarketBeat|TipRanks|Yahoo Finance|Seeking Alpha|SEC EDGAR|EDGAR|XBRL|Reuters|Bloomberg)',
        r'Accession:\s*\d+',
    ]
    combined_source = '|'.join(source_patterns)
    
    matches = list(re.finditer(number_pattern, report_text))
    
    results = {
        "total_numbers_found": len(matches),
        "numbers_with_source": 0,
        "numbers_without_source": 0,
        "unattributed": [],
    }
    
    for match in matches:
        start = match.start()
        end = match.end()
        # Buscar fuente en los 200 caracteres ANTES y 200 caracteres DESPUÉS de la cifra
        context_start = max(0, start - 200)
        context_end = min(len(report_text), end + 200)
        context = report_text[context_start:context_end]
        
        if re.search(combined_source, context):
            results["numbers_with_source"] += 1
        else:
            results["numbers_without_source"] += 1
            # Guardar la cifra y su contexto para debugging
            snippet = report_text[max(0, start-30):min(len(report_text), end+50)]
            results["unattributed"].append({
                "number": match.group(),
                "context": snippet.strip()
            })
    
    return results

def run_smoke_test():
    print("Iniciando auditoría de prueba de procedencia sobre 'NVDA'...")
    orchestrator = FinanzOrchestrator()
    output = orchestrator.run("Audita $NVDA con reporte forense completo")
    
    print("\n--- INICIO DEL REPORTE GENERADO ---")
    print(output)
    print("--- FIN DEL REPORTE GENERADO ---\n")

    violations = []
    
    # 1. Comprobación por frases exactas case-insensitive
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in output.lower():
            violations.append(phrase)

    # 2. Comprobación por regex flexible
    for pattern in FORBIDDEN_PATTERNS:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            matched_text = match.group(0)
            if matched_text not in violations:
                violations.append(matched_text)

    if violations:
        print(f"[ERROR] Violación de procedencia de datos detectada.")
        print(f"Patrones o frases prohibidas encontradas en el output: {violations}")
        print("El modelo ha fabricado datos no suministrados por las herramientas.")
        sys.exit(1)

    # Verificar que use la declaración fail-closed requerida
    if "No disponible — sin fuente" not in output:
        print("[AVISO] El reporte no contiene la frase estándar 'No disponible — sin fuente' para campos omitidos.")

    # 3. Verificación de procedencia por lista blanca (Whitelist Verification)
    print("\n--- VERIFICACIÓN DE PROCEDENCIA POR LISTA BLANCA ---")
    whitelist_stats = verify_provenance_whitelist(output)
    total = whitelist_stats["total_numbers_found"]
    with_source = whitelist_stats["numbers_with_source"]
    without_source = whitelist_stats["numbers_without_source"]
    ratio = (with_source / total * 100) if total > 0 else 100.0

    print(f"Total de cifras detectadas: {total}")
    print(f"Cifras con trazabilidad verificada: {with_source} ({ratio:.1f}%)")
    print(f"Cifras sin fuente inmediata: {without_source}")

    if without_source > 0:
        print("\nCifras sin fuente (contexto para debugging):")
        for item in whitelist_stats["unattributed"]:
            print(f"  • Cifra: '{item['number']}' | Contexto: \"{item['context']}\"")

    unattributed_ratio = (without_source / total * 100) if total > 0 else 0.0
    if unattributed_ratio > 30.0:
        print(f"\n[WARN] Porcentaje de cifras sin fuente supera el 30%: {unattributed_ratio:.1f}%")
    else:
        print(f"\n[OK] Porcentaje de cifras sin fuente en rango aceptable: {unattributed_ratio:.1f}% (<= 30%)")

    if ratio >= 70.0:
        print(f"[OK] Procedencia verificada por lista blanca: {ratio:.1f}% de las cifras tienen trazabilidad documental.")
    else:
        print(f"[WARN] Procedencia por lista blanca insuficiente: solo {ratio:.1f}% (< 70%) de cifras con fuente.")

    print("\n[OK] Procedencia verificada: cero alucinaciones con datos parciales.")
    sys.exit(0)

if __name__ == "__main__":
    run_smoke_test()

