"""Lookup handlers - chain of responsibility pattern"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from lookup.cache.base import CacheBase
from lookup.dictionary.service import DictionaryService
from lookup.domain import (
    ConjugationResult,
    SelectionData,
    TranslationResult,
    WordResult,
)
from lookup.translation.service import TranslationService

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
            # Only cache if result is WordResult with definitions
            if isinstance(result, WordResult) and result.definitions:
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
            # Always save with simple key so cache hits work without context
            simple_key = self.cache.make_simple_key(text)
            self.cache.set(simple_key, result, selection_data)
            # Also save with context key if there's a phrase
            if phrase:
                context_key = self.cache.make_context_key(text, phrase)
                self.cache.set(context_key, result, selection_data)
            return result
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return None
