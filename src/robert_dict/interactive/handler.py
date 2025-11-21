"""Input handling and service routing for dictionary lookups and translations"""

import logging
from typing import Optional, Union

from robert_dict.models import WordResult, TranslationResult
from robert_dict.services.dictionary import DictionaryService
from robert_dict.services.translation import ChatGPTTranslationService
from robert_dict.interactive.display import (
    display_word_result,
    display_translation_result,
    display_error
)


logger = logging.getLogger(__name__)


class InputHandler:
    """Handles user input and routes to appropriate services"""
    
    def __init__(
        self,
        dictionary_service: DictionaryService,
        translation_service: ChatGPTTranslationService
    ):
        self.dictionary_service = dictionary_service
        self.translation_service = translation_service
    
    def is_single_word(self, text: str) -> bool:
        """Check if input is a single word (no spaces)"""
        return len(text.strip().split()) == 1
    
    def process_input(
        self,
        text: str,
        context: Optional[str] = None
    ) -> Union[WordResult, TranslationResult, None]:
        """
        Process user input and return result
        
        Args:
            text: The word or phrase to look up
            context: Optional context for translation
            
        Returns:
            WordResult, TranslationResult, or None if error
        """
        text = text.strip()
        
        if not text:
            return None
        
        if self.is_single_word(text):
            # Try dictionary first
            return self._lookup_word_with_fallback(text, context)
        else:
            # Multiple words - use translation
            return self._translate_phrase(text, context)
    
    def _lookup_word_with_fallback(
        self,
        word: str,
        context: Optional[str] = None
    ) -> Union[WordResult, TranslationResult]:
        """
        Try dictionary lookup first, fallback to translation on 404
        
        Args:
            word: Single word to look up
            context: Optional context for fallback translation
            
        Returns:
            WordResult or TranslationResult
        """
        try:
            logger.debug(f"Looking up word in dictionary: {word}")
            result = self.dictionary_service.lookup_word(word)
            return result
        except ValueError as e:
            # Word not found (404)
            logger.debug(f"Word not found in dictionary, falling back to translation: {word}")
            return self._translate_phrase(word, context)
        except Exception as e:
            logger.error(f"Error looking up word: {e}")
            display_error(f"Failed to look up word: {e}")
            return None
    
    def _translate_phrase(
        self,
        phrase: str,
        context: Optional[str] = None
    ) -> Optional[TranslationResult]:
        """
        Translate phrase using translation service
        
        Args:
            phrase: Phrase to translate
            context: Optional context paragraph
            
        Returns:
            TranslationResult or None if error
        """
        try:
            logger.debug(f"Translating phrase: {phrase}")
            result = self.translation_service.translate(phrase, context)
            return result
        except Exception as e:
            logger.error(f"Error translating phrase: {e}")
            display_error(f"Failed to translate: {e}")
            return None
    
    def display_result(self, result: Union[WordResult, TranslationResult, None]):
        """Display the result using appropriate formatter"""
        if result is None:
            return
        
        if isinstance(result, WordResult):
            display_word_result(result)
        elif isinstance(result, TranslationResult):
            display_translation_result(result)

