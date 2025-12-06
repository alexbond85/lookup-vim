"""Lookup orchestration service"""

from __future__ import annotations

import logging

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

    def lookup(
        self, selection_data: SelectionData, handler: str | None = None
    ) -> LookupResult | None:
        """
        Perform lookup using chain or specific handler.

        Args:
            handler: Optional handler name ('dictionary', 'translation').
                    If None, uses automatic chain.
        """
        selection = selection_data.selection.strip()
        if not selection:
            return None

        # Direct handler invocation
        if handler is not None:
            if handler not in self._handlers:
                available = ", ".join(self._handlers.keys())
                raise ValueError(
                    f"Handler '{handler}' not found. Available: {available}"
                )
            logger.info(f"Using handler: {handler}")
            return self._handlers[handler].process(selection_data)

        # Default: use the chain
        if self._chain_head is None:
            return None
        return self._chain_head.handle(selection_data)
