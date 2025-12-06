from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lookup.domain import SelectionData


class CacheBase(ABC):
    """Abstract base class for cache implementations"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Get value from cache, return None if not found"""
        pass

    @abstractmethod
    def set(
        self, key: str, value: Any, context: "SelectionData | None" = None
    ) -> None:
        """Set value in cache with optional context"""
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass

    @staticmethod
    def make_simple_key(selection: str) -> str:
        """Create simple cache key for dictionary results"""
        return selection.strip().lower()

    @staticmethod
    def make_context_key(selection: str, phrase: str) -> str:
        """Create context-aware cache key for translation results"""
        return f"{selection.strip().lower()}||{phrase.strip()}"
