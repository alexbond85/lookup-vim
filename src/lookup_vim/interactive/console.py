"""Lightweight REPL for word lookup and translation"""

import logging
import os

from lookup_vim.cache import create_cache
from lookup_vim.interactive.display import (
    console,
    display_error,
    display_result,
)
from lookup_vim.models import (
    ConjugationResult,
    SelectionData,
    TranslationResult,
    WordResult,
)
from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.services.lookup_service import LookupService
from lookup_vim.services.translation import TranslationService
from lookup_vim.translation.scrapers.lerobert import LeRobertScraper
from lookup_vim.translation.translators.openai_llm import OpenAILLM
from lookup_vim.translation.translators.prompts import TranslationPrompts
from lookup_vim.translation.translators.translator import Translator

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class ConversationBuffer:
    """Manages follow-up conversation state with LLM"""

    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.messages: list[dict[str, str]] = []
        self.last_query: str | None = None
        self.last_result: str | None = None

    def start_conversation(self, query: str, result: str):
        """Start a new conversation with initial query and result"""
        self.messages = []
        self.last_query = query
        self.last_result = result

        self.messages.append(
            {
                "role": "system",
                "content": f"Aide à la lecture en {self.source_lang} pour locuteur {self.target_lang}. Parle {self.source_lang}/{self.target_lang} uniquement. Apprenant avancé. Réponses brèves et ciblées.",
            }
        )
        self.messages.append(
            {
                "role": "assistant",
                "content": f"Query: {query}\nResult: {result}",
            }
        )

    def add_follow_up(self, question: str) -> list[dict[str, str]]:
        """Add a follow-up question and return full conversation history"""
        self.messages.append({"role": "user", "content": question})
        return self.messages

    def add_response(self, response: str):
        """Add LLM response to conversation"""
        self.messages.append({"role": "assistant", "content": response})

    def has_conversation(self) -> bool:
        """Check if there's an active conversation"""
        return len(self.messages) > 0

    def reset(self):
        """Clear conversation state"""
        self.messages = []
        self.last_query = None
        self.last_result = None


class LookupConsole:
    """Lightweight REPL for word lookup and translation"""

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
        self.conversation_llm = OpenAILLM(model="gpt-5.1")
        translation_service = TranslationService(provider=translator)

        # Initialize lookup service
        self.lookup_service = LookupService(
            cache, dictionary_service, translation_service
        )

    def start(self):
        """Start the REPL loop"""
        console.print("[blue]Robert Lookup Console[/blue]\n")
        console.print("[dim]Enter word/phrase, [?] follow-up, [q] quit[/dim]\n")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n\nConsole stopped")

    def _main_loop(self):
        """Main REPL loop"""
        while True:
            self._display_prompt()

            try:
                user_input = input().strip()
            except EOFError:
                print("\nConsole stopped")
                return

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ("q", "quit", "exit"):
                print("\nConsole stopped")
                return

            if user_input == "?" and self.conversation.has_conversation():
                self._handle_follow_up_prompt()
                continue

            if user_input == "?":
                display_error("No active conversation for follow-up")
                continue

            # Regular lookup
            self._process_input(user_input)

    def _display_prompt(self):
        """Display input prompt with available options"""
        if self.conversation.has_conversation():
            console.print("[dim][?] follow-up | [q] quit[/dim]")
        console.print("[blue]>[/blue] ", end="")

    def _handle_follow_up_prompt(self):
        """Prompt for and handle follow-up question"""
        console.print("[dim]Follow-up question:[/dim]")
        console.print("[blue]>[/blue] ", end="")

        try:
            question = input().strip()
            if question:
                self._handle_follow_up(question)
        except EOFError:
            pass

    def _handle_follow_up(self, question: str):
        """Handle follow-up question about the last result"""
        console.print()

        try:
            messages = self.conversation.add_follow_up(question)

            response = self.conversation_llm.client.chat.completions.create(
                model=self.conversation_llm.model,
                messages=messages,
                temperature=0.7,
            )

            answer = response.choices[0].message.content
            self.conversation.add_response(answer)

            console.print("[blue]Answer:[/blue]\n")
            console.print(f"{answer}\n")

        except Exception as e:
            logger.error(f"Error in follow-up conversation: {e}")
            display_error(f"Failed to get response: {e}")

    def _process_input(self, user_input: str):
        """Process user input through lookup service"""
        self.conversation.reset()

        selection_data = SelectionData(
            selection=user_input, phrase="", paragraph="", file=""
        )

        result = self.lookup_service.lookup(selection_data)
        if result is None:
            display_error("Failed to lookup or translate")
            return

        display_result(result)

        # Start conversation for potential follow-ups
        result_text = self._format_result_for_conversation(result)
        self.conversation.start_conversation(user_input, result_text)

    def _format_result_for_conversation(self, result) -> str:
        """Format result as text for conversation context"""
        if isinstance(result, TranslationResult):
            return f"Translation: {result.translation}\nExplanations: {result.explanations}"
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
            return str(result)


def main():
    """Entry point for the lookup console"""
    cache_type = os.environ.get("CACHE_TYPE", "jsonl")
    service = LookupConsole(cache_type=cache_type)
    service.start()


if __name__ == "__main__":
    main()

