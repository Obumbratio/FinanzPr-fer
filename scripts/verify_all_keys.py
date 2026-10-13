"""
Script integral para verificar el estado de conexión de todas las API Keys configuradas en el proyecto.
No imprime claves sensibles en texto plano (enmascara todas las claves).
"""
import sys
import os
import time

# Asegurar UTF-8 en stdout de Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import settings

def mask_key(key: str) -> str:
    if not key or key in ("tu_clave_aqui", "tu_clave_fred_aqui", "tu_clave_finnhub_aqui", "tu_clave_fmp_aqui", "tu_clave_alphavantage_aqui"):
        return "[NO CONFIGURADA / VALOR DEFAULT]"
    if len(key) <= 8:
        return f"{key[:2]}***{key[-2:]} (longitud={len(key)})"
    return f"{key[:4]}...{key[-4:]} (longitud={len(key)})"

results = {}

print("=" * 75)
print("  VERIFICACIÓN INTEGRAL DE CONECTIVIDAD DE API KEYS - FINANZPRÜFER")
print("=" * 75)

# ---------------------------------------------------------
# 1. NEBIUS TOKEN FACTORY (NVIDIA Nemotron LLM - 3 Tiers)
# ---------------------------------------------------------
print("\n[1/7] Probando Nebius Token Factory (NVIDIA Nemotron - 3 Tiers)...")
nebius_key = settings.NEBIUS_API_KEY
masked_neb = mask_key(nebius_key)
print(f"  * Base URL: {settings.NEBIUS_BASE_URL}")
print(f"  * API Key: {masked_neb}")
print(f"  * Tier 1 Nano : {settings.MODEL_NANO}")
print(f"  * Tier 2 Super: {settings.MODEL_SUPER}")
print(f"  * Tier 3 Ultra: {settings.MODEL_ULTRA}")

if masked_neb.startswith("[NO CONFIGURADA"):
    results["NEBIUS"] = {"status": "FAIL", "reason": "NEBIUS_API_KEY no configurada o con valor default."}
else:
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=nebius_key,
            timeout=25.0
        )
        t0 = time.time()
        models = client.models.list()
        elapsed_list = time.time() - t0
        print(f"  -> Conexión y autenticación OK en {elapsed_list:.2f}s.")

        # Test Tier 1 Nano
        t1 = time.time()
        comp_nano = client.chat.completions.create(
            model=settings.MODEL_NANO,
            messages=[{"role": "user", "content": "Responde solo: OK"}],
            max_tokens=60
        )
        elapsed_nano = time.time() - t1
        print(f"  -> Inferencia Tier 1 Nano ({settings.MODEL_NANO}): OK en {elapsed_nano:.2f}s")

        results["NEBIUS"] = {
            "status": "SUCCESS",
            "details": f"Autenticado ({elapsed_list:.2f}s), Inferencia Nano OK ({elapsed_nano:.2f}s)"
        }
    except Exception as e:
        print(f"  -> ERROR de conexión con Nebius: {e}")
        results["NEBIUS"] = {"status": "FAIL", "reason": str(e)}

# ---------------------------------------------------------
# 2. TAVILY SEARCH API (Live Market Intelligence)
# ---------------------------------------------------------
print("\n[2/7] Probando Tavily Search API (Inteligencia de Mercado)...")
tavily_key = settings.TAVILY_API_KEY
masked_tav = mask_key(tavily_key)
print(f"  * API Key: {masked_tav}")

if masked_tav.startswith("[NO CONFIGURADA"):
    results["TAVILY"] = {"status": "FAIL", "reason": "TAVILY_API_KEY no configurada o con valor default."}
else:
    try:
        from tavily import TavilyClient
        t0 = time.time()
        client = TavilyClient(api_key=tavily_key)
        res = client.search(query="Apple financial results catalysts", max_results=2)
        elapsed = time.time() - t0
        num_res = len(res.get("results", []))
        if num_res > 0:
            sample_title = res["results"][0].get("title", "")[:45]
            print(f"  -> Búsqueda en vivo exitosa en {elapsed:.2f}s! ({num_res} noticias recibidas)")
            print(f"     Muestra: '{sample_title}...'")
            results["TAVILY"] = {"status": "SUCCESS", "details": f"Búsqueda OK ({elapsed:.2f}s, {num_res} resultados)"}
        else:
            results["TAVILY"] = {"status": "WARNING", "details": f"Búsqueda sin resultados ({elapsed:.2f}s)"}
    except Exception as e:
        print(f"  -> ERROR de conexión con Tavily: {e}")
        results["TAVILY"] = {"status": "FAIL", "reason": str(e)}

# ---------------------------------------------------------
# 3. FINNHUB API (Recomendaciones y Consenso de Analistas)
# ---------------------------------------------------------
print("\n[3/7] Probando Finnhub API (Consenso de analistas)...")
finnhub_key = settings.FINNHUB_API_KEY
masked_fin = mask_key(finnhub_key)
print(f"  * API Key: {masked_fin}")

if masked_fin.startswith("[NO CONFIGURADA"):
    results["FINNHUB"] = {"status": "FAIL", "reason": "FINNHUB_API_KEY no configurada o con valor default."}
else:
    try:
        from src.tools.search_tool import FinancialSearchTool
        t0 = time.time()
        st = FinancialSearchTool()
        res = st.get_recommendation_trends("AAPL")
        elapsed = time.time() - t0
        if res.get("status") == "SUCCESS":
            analysts = res.get("total_analysts")
            consensus = res.get("consensus")
            print(f"  -> Conectado exitosamente en {elapsed:.2f}s! Consenso AAPL: {consensus} (Analistas: {analysts})")
            results["FINNHUB"] = {"status": "SUCCESS", "details": f"Consenso AAPL: {consensus} ({elapsed:.2f}s, {analysts} analistas)"}
        else:
            print(f"  -> Respuesta Finnhub no exitosa: {res.get('reason')}")
            results["FINNHUB"] = {"status": "FAIL", "reason": res.get("reason")}
    except Exception as e:
        print(f"  -> ERROR de conexión con Finnhub: {e}")
        results["FINNHUB"] = {"status": "FAIL", "reason": str(e)}

# ---------------------------------------------------------
# 4. FRED API (Federal Reserve Economic Data)
# ---------------------------------------------------------
print("\n[4/7] Probando FRED API (Federal Reserve Economic Data)...")
fred_key = settings.FRED_API_KEY
masked_fred = mask_key(fred_key)
print(f"  * API Key: {masked_fred}")

if masked_fred.startswith("[NO CONFIGURADA"):
    results["FRED"] = {"status": "FAIL", "reason": "FRED_API_KEY no configurada o con valor default."}
else:
    try:
        from src.tools.fred_tool import FREDTool
        t0 = time.time()
        ft = FREDTool()
        obs = ft._fetch_series_observations("DGS10", limit=1)
        elapsed = time.time() - t0
        if obs and len(obs) > 0:
            val = obs[0].get("value")
            dt = obs[0].get("date")
            print(f"  -> Conectado exitosamente en {elapsed:.2f}s! (Treasury 10Y = {val}% al {dt})")
            results["FRED"] = {"status": "SUCCESS", "details": f"Treasury 10Y: {val}% ({elapsed:.2f}s al {dt})"}
        else:
            print(f"  -> Serie vacía en FRED.")
            results["FRED"] = {"status": "FAIL", "reason": "No se recibieron observaciones para DGS10"}
    except Exception as e:
        print(f"  -> ERROR de conexión con FRED: {e}")
        results["FRED"] = {"status": "FAIL", "reason": str(e)}

# ---------------------------------------------------------
# 5. FMP API (Financial Modeling Prep - Balances y Métricas)
# ---------------------------------------------------------
print("\n[5/7] Probando FMP API (Financial Modeling Prep)...")
fmp_key = settings.FMP_API_KEY
masked_fmp = mask_key(fmp_key)
print(f"  * API Key: {masked_fmp}")

if masked_fmp.startswith("[NO CONFIGURADA"):
    results["FMP"] = {"status": "FAIL", "reason": "FMP_API_KEY no configurada o con valor default."}
else:
    try:
        from src.tools.fmp_tool import FMPTool
        t0 = time.time()
        fm = FMPTool()
        res = fm.get_company_profile("AAPL")
        elapsed = time.time() - t0
        if res.get("status") == "SUCCESS":
            p = res.get("profile", {})
            name = p.get("company_name", "Apple Inc.")
            mcap_b = p.get("market_cap", 0) / 1e9
            print(f"  -> Conectado exitosamente en {elapsed:.2f}s! ({name} | MCap: ${mcap_b:.0f}B)")
            results["FMP"] = {"status": "SUCCESS", "details": f"Perfil AAPL OK ({elapsed:.2f}s, MCap ${mcap_b:.0f}B)"}
        else:
            print(f"  -> Respuesta FMP no exitosa: {res.get('reason')}")
            results["FMP"] = {"status": "FAIL", "reason": res.get("reason")}
    except Exception as e:
        print(f"  -> ERROR de conexión con FMP: {e}")
        results["FMP"] = {"status": "FAIL", "reason": str(e)}

# ---------------------------------------------------------
# 6. ALPHA VANTAGE API (Opcional)
# ---------------------------------------------------------
print("\n[6/7] Probando Alpha Vantage API (Opcional)...")
av_key = settings.ALPHA_VANTAGE_API_KEY
masked_av = mask_key(av_key)
print(f"  * API Key: {masked_av}")

if masked_av.startswith("[NO CONFIGURADA"):
    results["ALPHA_VANTAGE"] = {"status": "OPTIONAL_NOT_SET", "details": "Clave opcional no configurada en .env (no requerida)"}
    print("  -> Clave no configurada (servicio opcional, no afecta la operativa).")
else:
    try:
        import requests
        t0 = time.time()
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey={av_key}"
        resp = requests.get(url, timeout=10)
        elapsed = time.time() - t0
        data = resp.json()
        if "Global Quote" in data and data["Global Quote"]:
            price = data["Global Quote"].get("05. price", "N/A")
            print(f"  -> Conectado exitosamente en {elapsed:.2f}s! (IBM Price: {price})")
            results["ALPHA_VANTAGE"] = {"status": "SUCCESS", "details": f"Global Quote OK ({elapsed:.2f}s, price={price})"}
        elif "Note" in data:
            print(f"  -> Límite de peticiones de Alpha Vantage alcanzado: {data['Note'][:60]}...")
            results["ALPHA_VANTAGE"] = {"status": "RATE_LIMITED", "details": "Límite de frecuencia de API gratuita alcanzado"}
        elif "Error Message" in data:
            print(f"  -> Error en Alpha Vantage: {data['Error Message']}")
            results["ALPHA_VANTAGE"] = {"status": "FAIL", "reason": data["Error Message"]}
        else:
            results["ALPHA_VANTAGE"] = {"status": "PARTIAL", "details": str(data)[:60]}
    except Exception as e:
        print(f"  -> ERROR de conexión con Alpha Vantage: {e}")
        results["ALPHA_VANTAGE"] = {"status": "FAIL", "reason": str(e)}

# ---------------------------------------------------------
# 7. SEC EDGAR (Regulatorio - User-Agent Institucional)
# ---------------------------------------------------------
print("\n[7/7] Probando SEC EDGAR (SEC_USER_AGENT)...")
sec_ua = settings.SEC_USER_AGENT
print(f"  * User-Agent: {sec_ua}")

if not sec_ua or "@" not in sec_ua or "your_email@domain.com" in sec_ua:
    print(f"  -> AVISO: El User-Agent tiene el correo de ejemplo o formato no personalizado.")
    ua_warning = True
else:
    ua_warning = False

try:
    import requests
    t0 = time.time()
    headers = {"User-Agent": sec_ua}
    url = "https://data.sec.gov/submissions/CIK0000320193.json"  # Apple CIK
    resp = requests.get(url, headers=headers, timeout=10)
    elapsed = time.time() - t0
    if resp.status_code == 200:
        data = resp.json()
        entity = data.get("name", "Apple Inc.")
        filings_count = len(data.get("filings", {}).get("recent", {}).get("accessionNumber", []))
        print(f"  -> Conectado exitosamente en {elapsed:.2f}s! Entidad: {entity} ({filings_count} filings recientes)")
        status_sec = "SUCCESS (DEFAULT_EMAIL)" if ua_warning else "SUCCESS"
        results["SEC_EDGAR"] = {
            "status": status_sec,
            "details": f"Submissions OK ({elapsed:.2f}s, {filings_count} filings)" + (" [Recomendado personalizar email]" if ua_warning else "")
        }
    else:
        print(f"  -> Código de estado SEC: {resp.status_code}")
        results["SEC_EDGAR"] = {"status": "FAIL", "reason": f"HTTP {resp.status_code}"}
except Exception as e:
    print(f"  -> ERROR de conexión con SEC EDGAR: {e}")
    results["SEC_EDGAR"] = {"status": "FAIL", "reason": str(e)}

# ---------------------------------------------------------
# RESUMEN FINAL EJECUTIVO
# ---------------------------------------------------------
print("\n" + "=" * 75)
print("              TABLERO FINAL DE ESTADO DE APIS")
print("=" * 75)
print(f" {'SERVICIO':<18} | {'ESTADO':<20} | DETALLES")
print("-" * 75)

for api, res in results.items():
    st = res["status"]
    if st == "SUCCESS":
        icon = "[OK]"
    elif "DEFAULT_EMAIL" in st or "WARNING" in st or "RATE_LIMITED" in st:
        icon = "[WARN]"
    elif st == "OPTIONAL_NOT_SET":
        icon = "[INFO]"
    else:
        icon = "[FAIL]"
    
    det = res.get("details") or res.get("reason", "")
    print(f" {icon} {api:<13} | {st:<20} | {det}")

print("=" * 75)
