"""
Smoke test: verifica la funcionalidad de ToolCache (get, set, TTL, invalidación y aislamiento por clave).
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.cache import ToolCache, tool_cache

print("=" * 70)
print("VERIFICACION DE TOOL CACHE (MEMORIA + TTL)")
print("=" * 70)

# 1. Test singleton get / set
tool_cache.set("market:NVDA", {"price": 120.5, "score": 42.0})
hit = tool_cache.get("market:NVDA")
assert hit is not None, "Error: cache hit esperado para market:NVDA"
assert hit["price"] == 120.5, "Error: datos corruptos en cache"
print("  [OK] Cache set y get inmediato exitoso.")

# 2. Test aislamiento de claves
miss = tool_cache.get("market:TSLA")
assert miss is None, "Error: no debe existir market:TSLA aún"
print("  [OK] Aislamiento estricto de claves por ticker y herramienta.")

# 3. Test TTL expiration
short_cache = ToolCache(ttl_seconds=1)
short_cache.set("test:key", "valor_temporal")
assert short_cache.get("test:key") == "valor_temporal", "Error: valor temporal no recuperado"
time.sleep(1.2)
assert short_cache.get("test:key") is None, "Error: el valor debía haber expirado por TTL"
print("  [OK] Expiración automática por TTL verificada.")

# 4. Test clear
tool_cache.clear()
assert tool_cache.get("market:NVDA") is None, "Error: el cache debía estar vacío tras clear"
print("  [OK] Limpieza de cache (clear) verificada.")

print("=" * 70)
print("TOOL CACHE COMPLETAMENTE OPERATIVO.")
print("=" * 70)
