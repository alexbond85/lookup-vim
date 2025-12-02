from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from lookup_vim.cache.base import CacheBase
from lookup_vim.models import (
    ConjugationResult,
    SelectionData,
    TranslationResult,
    WordResult,
)
from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.services.translation import TranslationService

logger = logging.getLogger(__name__)

LookupResult = WordResult | ConjugationResult | TranslationResult


class LookupHandler(ABC):
    """Base handler for chain of responsibility. Override 'name' in subclasses."""

    name: str = "base"

    def __init__(self):
        self._next_handler: LookupHandler | None = None

    def set_next(self, handler: LookupHandler) -> LookupHandler:
        """Set the next handler in the chain. Returns handler for chaining."""
        self._next_handler = handler
        return handler

    def handle(self, selection_data: SelectionData) -> LookupResult | None:
        """Process request. Returns result if successful, None to continue chain."""
        if not self.can_handle(selection_data):
            return self._pass_to_next(selection_data)

        result = self.process(selection_data)

        if self.should_stop(result):
            return result
        return self._pass_to_next(selection_data)

    @abstractmethod
    def can_handle(self, selection_data: SelectionData) -> bool:
        """Should this handler process the request?"""
        pass

    @abstractmethod
    def process(self, selection_data: SelectionData) -> LookupResult | None:
        """Process the request."""
        pass

    def should_stop(self, result: LookupResult | None) -> bool:
        """Should chain stop? Default: stop if result is not None."""
        return result is not None

    def _pass_to_next(
        self, selection_data: SelectionData
    ) -> LookupResult | None:
        """Pass to next handler"""
        if self._next_handler:
            return self._next_handler.handle(selection_data)
        return None


class CacheHandler(LookupHandler):
    """Checks cache before other processing"""

    name = "cache"

    def __init__(self, cache: CacheBase):
        super().__init__()
        self.cache = cache

    def can_handle(self, _selection_data: SelectionData) -> bool:
        return True

    def process(self, selection_data: SelectionData) -> LookupResult | None:
        selection = selection_data.selection.strip()
        phrase = selection_data.phrase.strip()

        simple_key = self.cache.make_simple_key(selection)
        if self.cache.has(simple_key):
            logger.debug(f"Cache hit: {simple_key}")
            return self.cache.get(simple_key)

        if phrase:
            context_key = self.cache.make_context_key(selection, phrase)
            if self.cache.has(context_key):
                logger.debug(f"Cache hit: {context_key}")
                return self.cache.get(context_key)

        return None


class DictionaryHandler(LookupHandler):
    """Looks up single words in dictionary"""

    name = "dictionary"

    def __init__(
        self, dictionary_service: DictionaryService, cache: CacheBase
    ):
        super().__init__()
        self.dictionary_service = dictionary_service
        self.cache = cache

    def can_handle(self, selection_data: SelectionData) -> bool:
        selection = selection_data.selection.strip()
        return len(selection.split()) == 1

    def process(self, selection_data: SelectionData) -> LookupResult | None:
        word = selection_data.selection.strip().rstrip(",.!?;:")
        try:
            result = self.dictionary_service.lookup_word(word)
            simple_key = self.cache.make_simple_key(word)
            self.cache.set(simple_key, result, selection_data)
            return result
        except ValueError:
            logger.debug(f"Dictionary 404: {word}")
            return None
        except Exception as e:
            logger.error(f"Dictionary error: {e}")
            return None

    def should_stop(self, result: LookupResult | None) -> bool:
        """Stop only if result has definitions"""
        if isinstance(result, WordResult) and not result.definitions:
            logger.debug("Empty result, continuing to translation")
            return False
        return result is not None


class TranslationHandler(LookupHandler):
    """Translates text (fallback)"""

    name = "translation"

    def __init__(
        self, translation_service: TranslationService, cache: CacheBase
    ):
        super().__init__()
        self.translation_service = translation_service
        self.cache = cache

    def can_handle(self, _selection_data: SelectionData) -> bool:
        return True

    def process(self, selection_data: SelectionData) -> LookupResult | None:
        text = selection_data.selection.strip()
        phrase = selection_data.phrase.strip()

        try:
            result = self.translation_service.translate(
                text, phrase if phrase else None
            )
            context_key = self.cache.make_context_key(text, phrase)
            self.cache.set(context_key, result, selection_data)
            return result
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return None


class LookupService:
    """Orchestrates lookup handlers. Use lookup() for automatic chain or specify handler."""

    def __init__(
        self,
        cache: CacheBase,
        dictionary_service: DictionaryService,
        translation_service: TranslationService,
    ):
        self.cache = cache
        self.dictionary_service = dictionary_service
        self.translation_service = translation_service

        # Handler registry for direct access
        self._handlers: dict[str, LookupHandler] = {}

        # Build the default chain and populate registry
        self._build_chain()

    def _build_chain(self) -> None:
        """Build handler chain: Cache → Dictionary → Translation"""
        cache_handler = CacheHandler(self.cache)
        dict_handler = DictionaryHandler(self.dictionary_service, self.cache)
        trans_handler = TranslationHandler(
            self.translation_service, self.cache
        )

        # Register handlers
        self._handlers = {
            cache_handler.name: cache_handler,
            dict_handler.name: dict_handler,
            trans_handler.name: trans_handler,
        }

        # Chain them
        cache_handler.set_next(dict_handler).set_next(trans_handler)
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
        return self._chain_head.handle(selection_data)
