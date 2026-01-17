"""Lookup orchestration service"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TypeVar

from lookup.cache.base import CacheBase
from lookup.dictionary.service import DictionaryService
from lookup.domain import (
    ConjugationResult,
    SelectionData,
    TranslationResult,
    WordResult,
)
from lookup.orchestration.handlers import (
    CacheHandler,
    DictionaryHandler,
    LookupHandler,
    TranslationHandler,
)
from lookup.translation.service import TranslationService

logger = logging.getLogger(__name__)

LookupResult = WordResult | ConjugationResult | TranslationResult
T = TypeVar("T")


@dataclass
class LookupResponse:
    """Wrapper for lookup result with metadata"""
    result: LookupResult | None
    from_cache: bool = False


class LookupService:
    """Orchestrates lookup handlers.

    Required: cache, translation_service
    Optional: dictionary_service (use .with_dictionary())

    Usage:
        service = (
            LookupService(cache, translation_service)
            .with_dictionary(dictionary_service)
        )
    """

    def __init__(
        self,
        cache: CacheBase,
        translation_service: TranslationService,
    ):
        self._cache = cache
        self._translation_service = translation_service
        self._dictionary_service: DictionaryService | None = None

        # Handler registry for direct access
        self._handlers: dict[str, LookupHandler] = {}
        self._chain_head: LookupHandler | None = None

        self._build_chain()

    def with_dictionary(self, service: DictionaryService) -> LookupService:
        """Add dictionary lookup to the chain"""
        self._dictionary_service = service
        self._build_chain()
        return self

    def _build_chain(self) -> None:
        """Build handler chain: Cache → [Dictionary] → Translation"""
        cache_handler = CacheHandler(self._cache)
        trans_handler = TranslationHandler(
            self._translation_service, self._cache
        )

        # Register handlers
        self._handlers = {
            cache_handler.name: cache_handler,
            trans_handler.name: trans_handler,
        }

        # Build chain based on available services
        if self._dictionary_service:
            dict_handler = DictionaryHandler(
                self._dictionary_service, self._cache
            )
            self._handlers[dict_handler.name] = dict_handler
            cache_handler.set_next(dict_handler).set_next(trans_handler)
        else:
            cache_handler.set_next(trans_handler)

        self._chain_head = cache_handler

    def _is_cached(self, selection_data: SelectionData) -> bool:
        """Check if selection is already in cache"""
        selection = selection_data.selection.strip()
        phrase = selection_data.phrase.strip()

        simple_key = self._cache.make_simple_key(selection)
        if self._cache.has(simple_key):
            return True

        if phrase:
            context_key = self._cache.make_context_key(selection, phrase)
            if self._cache.has(context_key):
                return True

        return False

    def lookup(
        self, selection_data: SelectionData, handler: str | None = None
    ) -> LookupResponse:
        """
        Perform lookup using chain or specific handler.

        Args:
            handler: Optional handler name ('dictionary', 'translation').
                    If None, uses automatic chain.

        Returns:
            LookupResponse with result and from_cache flag.
        """
        selection = selection_data.selection.strip()
        if not selection:
            return LookupResponse(result=None, from_cache=False)

        # Check cache status before processing
        from_cache = self._is_cached(selection_data)

        # Direct handler invocation
        if handler is not None:
            if handler not in self._handlers:
                available = ", ".join(self._handlers.keys())
                raise ValueError(
                    f"Handler '{handler}' not found. Available: {available}"
                )
            logger.info(f"Using handler: {handler}")
            result = self._handlers[handler].process(selection_data)
            return LookupResponse(result=result, from_cache=from_cache)

        # Default: use the chain
        if self._chain_head is None:
            return LookupResponse(result=None, from_cache=False)

        result = self._chain_head.handle(selection_data)
        return LookupResponse(result=result, from_cache=from_cache)
