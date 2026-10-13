"""
Smoke test: verifica que get_analyst_consensus devuelve datos reales de Tavily.
"""
import sys
import os

# Asegurar path raíz y encoding UTF-8 en Windows
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.tools.search_tool import FinancialSearchTool

tool = FinancialSearchTool()

for ticker in ["NVDA", "TSLA"]:
    print(f"\n{'='*60}")
    print(f"CONSENSO DE ANALISTAS: ${ticker}")
    print(f"{'='*60}")
    
    result = tool.get_analyst_consensus(ticker)
    
    print(f"  Status: {result['status']}")
    
    if result["status"] == "SUCCESS":
        print(f"  Resultados totales: {result['raw_result_count']}")
        for search in result["search_results"]:
            print(f"\n  Query: {search['query']}")
            for r in search["results"][:3]:  # primeros 3 de cada query
                print(f"    - [{r.get('source_domain', 'N/A')}] {r['title'][:80]}")
                print(f"      URL: {r['url']}")
                snippet_preview = r['snippet'][:120] + "..." if len(r['snippet']) > 120 else r['snippet']
                print(f"      Snippet: {snippet_preview}")
        
        # Asserts
        assert result["raw_result_count"] > 0, f"No results for {ticker}"
        assert len(result["search_results"]) >= 2, f"Expected at least 2 query groups for {ticker}"
        for search in result["search_results"]:
            for r in search["results"]:
                assert "url" in r and r["url"].startswith("http"), f"Invalid URL in result"
                assert "snippet" in r and len(r["snippet"]) > 10, f"Empty snippet"
        print(f"\n  * [OK] ${ticker}: Consenso verificado con {result['raw_result_count']} resultados.")
    else:
        print(f"  Razón: {result.get('reason', 'Unknown')}")
        print(f"  * [WARN] ${ticker}: Sin datos de consenso disponibles.")

print(f"\n{'='*60}")
print("VERIFICACIÓN DE CONSENSO DE ANALISTAS COMPLETADA.")
print(f"{'='*60}")
