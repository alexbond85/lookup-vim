from lookup_vim.cache.base import CacheBase
from lookup_vim.cache.csv_cache import CSVCache
from lookup_vim.cache.memory import MemoryCache

__all__ = ["CacheBase", "MemoryCache", "CSVCache", "create_cache"]


def create_cache(cache_type: str = "memory") -> CacheBase:
    """Factory function to create cache instances"""
    if cache_type == "csv":
        return CSVCache()
    return MemoryCache()
