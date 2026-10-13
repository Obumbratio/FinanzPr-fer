import time
from typing import Any, Optional

class ToolCache:
    """Simple in-memory cache with TTL for tool results."""

    def __init__(self, ttl_seconds: int = 900):  # 15 minutos por defecto
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            timestamp, value = self._store[key]
            if time.time() - timestamp < self._ttl:
                return value
            else:
                try:
                    del self._store[key]
                except KeyError:
                    pass
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        self._store.clear()

# Singleton instance
tool_cache = ToolCache()
