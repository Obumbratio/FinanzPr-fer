import sys
import time
sys.path.insert(0, ".")

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import settings
from src.tools.search_tool import FinancialSearchTool

def test_tavily_search():
    settings.validate_nebius()
    
    print("=" * 65)
    print("FINANZPRÜFER: TEST DE BÚSQUEDA WEB FINANCIERA (TAVILY API)")
    print("=" * 65)
    
    search_tool = FinancialSearchTool()
    
    if not search_tool.is_configured():
        print("[AVISO]: Tavily API Key no detectada. Operando en modo fallback local.")
        return

    masked_key = f"{settings.TAVILY_API_KEY[:6]}...{settings.TAVILY_API_KEY[-4:]}"
    print(f"API Key detectada: {masked_key}")
    
    query = "NVDA earnings expectations"
    print(f"Buscando contexto de mercado para: '{query}'...\n")

    start_time = time.time()
    try:
        results = search_tool.search_market_news(query=query, max_results=3)
        latency = time.time() - start_time

        print(f"[CONEXIÓN EXITOSA - Latencia: {latency:.2f}s]")
        print(f"Resultados recuperados: {len(results)}\n")
        print("-" * 65)

        for i, item in enumerate(results, 1):
            title = item.get("title", "N/A")
            url = item.get("url", "N/A")
            snippet = item.get("content", "")[:120] + "..."
            score = item.get("score", 0.0)
            date = item.get("published_date", "N/A")

            print(f"{i}. {title}")
            print(f"   URL:   {url}")
            print(f"   Score: {score} | Fecha: {date}")
            print(f"   Cuerpo: {snippet}\n")
        
        print("=" * 65)
    except Exception as e:
        print(f"[ERROR EN BÚSQUEDA]: {e}")

if __name__ == "__main__":
    test_tavily_search()
