"""Core lookup engine - input-agnostic

This module contains the core lookup logic without any input handling.
Input handling is delegated to the runner module.
"""

import logging

from lookup_vim.cache import create_cache
from lookup_vim.models import (
    ConjugationResult,
    SelectionData,
    TranslationResult,
    WordResult,
)
from lookup_vim.repl.followup import ConversationBuffer
from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.services.lookup_service import LookupService
from lookup_vim.services.translation import TranslationService
from lookup_vim.translation.scrapers.lerobert import LeRobertScraper
from lookup_vim.translation.translators.openai_llm import OpenAILLM
from lookup_vim.translation.translators.prompts import TranslationPrompts
from lookup_vim.translation.translators.translator import Translator

logger = logging.getLogger(__name__)


LookupResult = WordResult | ConjugationResult | TranslationResult | None


class LookupEngine:
    """Core lookup engine - performs lookups and manages conversation state

    This class is input-agnostic. It receives SelectionData and returns results.
    Input handling (stdin, FIFO, etc.) is handled by the runner.
    """

    def __init__(
        self,
        cache_type: str = "memory",
        source_lang: str = "French",
        target_lang: str = "Russian",
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang

        # Conversation buffer for follow-up questions
        self.conversation = ConversationBuffer(source_lang, target_lang)

        # Initialize cache
        cache = create_cache(cache_type)

        # Initialize services
        scraper = LeRobertScraper()
        dictionary_service = DictionaryService(scraper)

        # LLM for translation
        translation_llm = OpenAILLM(model="gpt-5.1")
        prompts = TranslationPrompts.create(
            source_lang=source_lang, target_lang=target_lang
        )
        translator = Translator(
            structured_llm=translation_llm,
            prompts=prompts,
        )

        # Separate LLM for follow-up conversations
        self._conversation_llm = OpenAILLM(model="gpt-5.1")
        translation_service = TranslationService(provider=translator)

        # Initialize lookup service
        self._lookup_service = LookupService(
            cache, dictionary_service, translation_service
        )

    def lookup(self, data: SelectionData) -> LookupResult:
        """Perform lookup and start conversation context

        Args:
            data: Selection data containing text and context

        Returns:
            WordResult, ConjugationResult, TranslationResult, or None
        """
        if not data.selection:
            return None

        # Reset conversation for new lookup
        self.conversation.reset()

        result = self._lookup_service.lookup(data)
        if result is None:
            return None

        # Start conversation context for potential follow-ups
        result_text = self._format_result_for_conversation(result)
        self.conversation.init_conversation(data.selection, result_text)

        return result

    def follow_up(self, question: str) -> str | None:
        """Ask a follow-up question about the last result

        Args:
            question: The follow-up question

        Returns:
            LLM response or None on error
        """
        if not self.conversation.has_conversation():
            return None

        try:
            messages = self.conversation.add_follow_up(question)
            answer = self._conversation_llm.chat(messages)
            if answer:
                self.conversation.add_response(answer)

            return answer

        except Exception as e:
            logger.error(f"Error in follow-up conversation: {e}")
            return None

    def _format_result_for_conversation(self, result: LookupResult) -> str:
        """Format result as text for conversation context"""
        if isinstance(result, TranslationResult):
            return (
                f"Translation: {result.translation}\n"
                f"Explanations: {result.explanations}"
            )
        elif isinstance(result, WordResult):
            lines = []
            for i, d in enumerate(result.definitions, 1):
                lines.append(f"{i}. {d.definition}")
                for ex in d.examples[:2]:
                    lines.append(f"   → {ex}")
            definitions = "\n".join(lines)
            return f"Word: {result.word}\nDefinitions:\n{definitions}"
        elif isinstance(result, ConjugationResult):
            return f"Conjugation of: {result.redirected_to}\n{result.message}"
        else:
            return str(result) if result else ""
