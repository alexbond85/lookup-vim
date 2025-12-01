import logging

from lookup_vim.cache.base import CacheBase
from lookup_vim.models import (
    ConjugationResult,
    Definition,
    SelectionData,
    TranslationResult,
    WordResult,
)
from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.services.translation import TranslationService

logger = logging.getLogger(__name__)


class LookupDataLayer:
    """Data layer handling lookup logic with smart caching"""

    def __init__(
        self,
        cache: CacheBase,
        dictionary_service: DictionaryService,
        translation_service: TranslationService,
    ):
        self.cache = cache
        self.dictionary_service = dictionary_service
        self.translation_service = translation_service

    def lookup(
        self, selection_data: SelectionData
    ) -> WordResult | ConjugationResult | TranslationResult | None:
        """
        Lookup selection with smart caching strategy:
        - Dictionary results cached by selection only
        - Translation results cached by (selection, phrase)
        """
        selection = selection_data.selection.strip()
        phrase = selection_data.phrase.strip()

        if not selection:
            return None

        # Try simple cache key first (dictionary results)
        simple_key = self.cache.make_simple_key(selection)
        if self.cache.has(simple_key):
            logger.debug(f"Cache hit (simple): {simple_key}")
            cached = self.cache.get(simple_key)
            if cached is not None:
                return self._deserialize_result(cached)

        # Try context cache key (translation results)
        if phrase:
            context_key = self.cache.make_context_key(selection, phrase)
            if self.cache.has(context_key):
                logger.debug(f"Cache hit (context): {context_key}")
                cached = self.cache.get(context_key)
                if cached is not None:
                    return self._deserialize_result(cached)

        # Not in cache - determine lookup strategy
        is_single_word = len(selection.split()) == 1

        if is_single_word:
            return self._lookup_single_word(
                selection, phrase, simple_key, selection_data
            )
        else:
            return self._lookup_phrase(selection, phrase, selection_data)

    def _lookup_single_word(
        self,
        word: str,
        phrase: str,
        simple_key: str,
        selection_data: SelectionData,
    ) -> WordResult | ConjugationResult | TranslationResult | None:
        """Lookup single word with dictionary, fallback to translation"""
        try:
            result = self.dictionary_service.lookup_word(word)

            # Check if result is meaningful (has definitions or is a conjugation)
            if isinstance(result, WordResult) and not result.definitions:
                logger.debug(
                    f"Dictionary returned empty result, falling back to translation: {word}"
                )
                return self._lookup_phrase(word, phrase, selection_data)

            # Try to cache, but don't fail if caching fails
            try:
                self.cache.set(
                    simple_key, self._serialize_result(result), selection_data
                )
                logger.debug(f"Cached dictionary result: {simple_key}")
            except Exception as cache_error:
                logger.warning(
                    f"Failed to cache result for {simple_key}: {cache_error}"
                )
            return result
        except ValueError:
            # Word not found in dictionary - fallback to translation
            logger.debug(
                f"Dictionary 404, falling back to translation: {word}"
            )
            return self._lookup_phrase(word, phrase, selection_data)
        except Exception as e:
            logger.error(f"Error looking up word: {e}")
            return None

    def _lookup_phrase(
        self, text: str, phrase: str, selection_data: SelectionData
    ) -> TranslationResult | None:
        """Translate phrase and cache with context key"""
        try:
            context = phrase if phrase else None
            result = self.translation_service.translate(text, context)
            # Try to cache, but don't fail if caching fails
            try:
                context_key = self.cache.make_context_key(text, phrase or "")
                self.cache.set(
                    context_key, self._serialize_result(result), selection_data
                )
                logger.debug(f"Cached translation result: {context_key}")
            except Exception as cache_error:
                logger.warning(f"Failed to cache translation: {cache_error}")
            return result
        except Exception as e:
            logger.error(f"Error translating phrase: {e}")
            return None

    def _serialize_result(
        self, result: WordResult | ConjugationResult | TranslationResult
    ) -> dict:
        """Convert result to dict for caching"""
        # Manual serialization to ensure JSON compatibility
        if isinstance(result, WordResult):
            return {
                "type": "WordResult",
                "data": {
                    "word": result.word,
                    "url": result.url,
                    "original_word": result.original_word,
                    "definitions": [
                        {
                            "category": d.category,
                            "definition": d.definition,
                            "examples": d.examples,
                        }
                        for d in result.definitions
                    ],
                    "usage_examples": result.usage_examples,
                    "word_combinations": result.word_combinations,
                },
            }
        elif isinstance(result, ConjugationResult):
            return {
                "type": "ConjugationResult",
                "data": {
                    "original_word": result.original_word,
                    "redirected_to": result.redirected_to,
                    "url": result.url,
                    "definition_url": result.definition_url,
                    "conjugations_sample": result.conjugations_sample,
                    "message": result.message,
                },
            }
        elif isinstance(result, TranslationResult):
            return {
                "type": "TranslationResult",
                "data": {
                    "query": result.query,
                    "translation": result.translation,
                    "explanations": result.explanations,
                    "context": result.context,
                },
            }
        else:
            raise TypeError(f"Unknown result type: {type(result)}")

    def _deserialize_result(
        self, data: dict
    ) -> WordResult | ConjugationResult | TranslationResult | None:
        """Convert cached dict back to result object"""
        # If data is already a result object (from memory cache), return as-is
        if isinstance(
            data, (WordResult, ConjugationResult, TranslationResult)
        ):
            return data

        result_type = data.get("type")
        result_data = data.get("data", {})

        if result_type == "WordResult":
            # Convert definition dicts back to Definition objects
            definitions = []
            for d in result_data.get("definitions", []):
                # Check if already a Definition object
                if isinstance(d, Definition):
                    definitions.append(d)
                else:
                    definitions.append(Definition(**d))
            result_data["definitions"] = definitions
            return WordResult(**result_data)
        elif result_type == "ConjugationResult":
            return ConjugationResult(**result_data)
        elif result_type == "TranslationResult":
            return TranslationResult(**result_data)
        return None
