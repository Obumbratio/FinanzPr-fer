import sys
import time
from src.config import settings
from src.tools.search_tool import FinancialSearchTool

def test_tavily_connection():
    print("=" * 65)
    print("FINANZPRÜFER: TEST DE BÚSQUEDA WEB FINANCIERA (TAVILY API)")
    print("=" * 65)

    # 1. Validación de API Key
    if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY == "tu_clave_aqui":
        print("[ERROR CRÍTICO] TAVILY_API_KEY no está configurada en .env")
        print("Por favor, coloca tu clave de Tavily (tvly-...) en el archivo .env")
        sys.exit(1)

    print(f"API Key detectada: {settings.TAVILY_API_KEY[:6]}...{settings.TAVILY_API_KEY[-4:]}")
    
    # 2. Inicialización y ejecución
    tool = FinancialSearchTool()
    ticker_query = "NVDA earnings expectations"
    print(f"Buscando contexto de mercado para: '{ticker_query}'...\n")

    start_time = time.time()
    results = tool.search_market_news(query=ticker_query, max_results=3)
    latency = time.time() - start_time

    # 3. Inspección de resultados
    print(f"[CONEXIÓN EXITOSA - Latencia: {latency:.2f}s]")
    print(f"Resultados recuperados: {len(results)}\n")
    print("-" * 65)

    for i, item in enumerate(results, 1):
        print(f"{i}. {item['title']}")
        print(f"   URL:   {item['url']}")
        print(f"   Score: {item.get('score', 0.0)} | Fecha: {item.get('published_date', 'N/A')}")
        print(f"   Cuerpo: {item['content'][:140]}...\n")

    print("=" * 65)

if __name__ == "__main__":
    test_tavily_connection()
