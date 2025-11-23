from typing import TYPE_CHECKING, Any

from lookup_vim.cache.base import CacheBase

if TYPE_CHECKING:
    from lookup_vim.models import SelectionData


class MemoryCache(CacheBase):
    """In-memory cache implementation using a dict"""

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    def set(
        self, key: str, value: Any, _context: "SelectionData | None" = None
    ) -> None:
        self._cache[key] = value

    def has(self, key: str) -> bool:
        return key in self._cache
