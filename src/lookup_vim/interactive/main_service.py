"""Main lookup service with FIFO reading and smart caching"""

import json
import logging
import os
import select
import sys
from pathlib import Path

from lookup_vim.cache import create_cache
from lookup_vim.constants import FIFO_PATH
from lookup_vim.data_layer import LookupDataLayer
from lookup_vim.interactive.display import (
    console,
    display_error,
    display_result,
)
from lookup_vim.interactive.history import HistoryLogger
from lookup_vim.models import SelectionData
from lookup_vim.scrapers.lerobert import LeRobertScraper
from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.services.translation import TranslationService
from lookup_vim.translators.chatgpt import ChatGPTTranslator
from lookup_vim.translators.llm import StructuredLLM

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

        # Add system context and initial result
        self.messages.append({
            "role": "system",
            "content": f"Aide à la lecture en {self.source_lang} pour locuteur {self.target_lang}. Parle {self.source_lang}/{self.target_lang} uniquement. Apprenant avancé. Réponses brèves et ciblées."
        })
        self.messages.append({
            "role": "assistant",
            "content": f"Query: {query}\nResult: {result}"
        })

    def add_follow_up(self, question: str) -> list[dict[str, str]]:
        """Add a follow-up question and return full conversation history"""
        self.messages.append({
            "role": "user",
            "content": question
        })
        return self.messages

    def add_response(self, response: str):
        """Add LLM response to conversation"""
        self.messages.append({
            "role": "assistant",
            "content": response
        })

    def has_conversation(self) -> bool:
        """Check if there's an active conversation"""
        return len(self.messages) > 0

    def reset(self):
        """Clear conversation state"""
        self.messages = []
        self.last_query = None
        self.last_result = None


class MainLookupService:
    """Main service coordinating FIFO reading and data layer"""

    def __init__(self, fifo_path: Path, cache_type: str = "memory", 
                 source_lang: str = "French", target_lang: str = "Russian"):
        self.fifo_path = fifo_path
        self.fifo = None
        self.source_lang = source_lang
        self.target_lang = target_lang

        # Current context for phrase/paragraph translation options
        self.current_phrase: str | None = None
        self.current_paragraph: str | None = None

        # Conversation buffer for follow-up questions
        self.conversation = ConversationBuffer(source_lang, target_lang)

        # Initialize cache
        cache = create_cache(cache_type)

        # Initialize services
        scraper = LeRobertScraper()
        dictionary_service = DictionaryService(scraper)

        # LLM for translation
        translation_llm = StructuredLLM(
            model="gpt-5.1",
            system_prompt=f"Aide à la lecture en {source_lang} pour locuteur {target_lang}. Parle {source_lang}/{target_lang} uniquement. Apprenant avancé. Traduction en {target_lang}, explications brèves et ciblées.",
        )
        translator = ChatGPTTranslator(
            llm=translation_llm, source_lang=source_lang, target_lang=target_lang
        )
        
        # Separate LLM for follow-up conversations (no structured output)
        self.conversation_llm = StructuredLLM(
            model="gpt-5.1",
            system_prompt=""  # Will be set per conversation
        )
        translation_service = TranslationService(provider=translator)

        # Initialize data layer
        self.data_layer = LookupDataLayer(
            cache, dictionary_service, translation_service
        )

        # Initialize history logger
        self.history = HistoryLogger(console)

    def start(self):
        """Start the service and listen on FIFO"""
        console.print(
            "[blue]Robert Lookup Service[/blue]\n"
        )

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n\nService stopped")
        finally:
            self._cleanup()
            self.history.save_session()

    def _open_fifo(self):
        """Create and open FIFO in non-blocking mode"""
        if not self.fifo_path.exists():
            os.mkfifo(self.fifo_path)
            logger.info(f"Created FIFO at {self.fifo_path}")

        fd = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        return os.fdopen(fd, "r")

    def _cleanup(self):
        """Cleanup FIFO resources"""
        if self.fifo:
            try:
                self.fifo.close()
            except Exception as e:
                logger.debug(f"Error closing FIFO: {e}")

    def _main_loop(self):
        """Main event loop: read from FIFO and console input"""
        self.fifo = self._open_fifo()
        console.print(
            "[dim]Ready for input from Vim or console[/dim]\n"
        )
        print_prompt = True

        while True:
            # Display prompt when needed
            if print_prompt:
                self._display_prompt()
                print_prompt = False

            # Wait for input from either stdin or FIFO
            try:
                ready, _, _ = select.select([sys.stdin, self.fifo], [], [], 1.0)
            except OSError:
                # Handle interrupted system call
                continue

            # Check FIFO for Vim selections
            if self.fifo in ready:
                try:
                    assert self.fifo is not None
                    line = self.fifo.readline().strip()
                    if line:
                        data = json.loads(line)
                        selection_data = SelectionData(
                            selection=data.get("selection", ""),
                            phrase=data.get("phrase", ""),
                            paragraph=data.get("paragraph", ""),
                            file=data.get("file", ""),
                        )
                        # Save context for options 1/2
                        self.current_phrase = selection_data.phrase or None
                        self.current_paragraph = selection_data.paragraph or None
                        
                        # Reset conversation on new Vim selection
                        self.conversation.reset()
                        
                        self._process_selection(selection_data)
                        print_prompt = True
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from FIFO: {e}")
                except Exception as e:
                    logger.error(f"Error reading from FIFO: {e}")

            # Check stdin for console input
            if sys.stdin in ready:
                try:
                    user_input = input().strip()
                    print_prompt = True

                    if user_input == "":
                        continue

                    # Check for exit command
                    if user_input.lower() in ("q", "quit", "exit"):
                        print("\nService stopped")
                        return

                    # Process user input
                    self._process_console_input(user_input)

                except EOFError:
                    print("\nService stopped")
                    return

    def _display_prompt(self):
        """Display input prompt with available options"""
        has_context = bool(self.current_phrase or self.current_paragraph)
        has_conversation = self.conversation.has_conversation()
        
        if has_context or has_conversation:
            options = []
            if self.current_phrase:
                options.append("[1] Translate phrase")
            if self.current_paragraph:
                options.append("[2] Translate paragraph")
            if has_conversation:
                options.append("[3] Follow-up question")
            options.append("[q/exit] Quit")
            
            console.print(f"[dim]Options: {' | '.join(options)}[/dim]")
        else:
            console.print(
                "[dim]Enter word/phrase or [q/exit] to quit[/dim]"
            )
        console.print("[blue]>[/blue] ", end="")

    def _process_console_input(self, user_input: str):
        """Process console input with special commands and multi-line paste support"""
        # Check for special commands (1/2/3 for context/conversation)
        if user_input == "1" and self.current_phrase:
            # Translate phrase - reset conversation
            self.conversation.reset()
            selection_data = SelectionData(
                selection=self.current_phrase,
                phrase="",
                paragraph="",
                file=""
            )
            self._process_selection(selection_data)
            return
        
        if user_input == "2" and self.current_paragraph:
            # Translate paragraph - reset conversation
            self.conversation.reset()
            selection_data = SelectionData(
                selection=self.current_paragraph,
                phrase="",
                paragraph="",
                file=""
            )
            self._process_selection(selection_data)
            return
        
        if user_input == "3" and self.conversation.has_conversation():
            # Follow-up question - keep asking until we get the question
            console.print("[dim]Follow-up question:[/dim]")
            console.print("[blue]>[/blue] ", end="")
            try:
                question = input().strip()
                if question:
                    self._handle_follow_up(question)
            except EOFError:
                pass
            return
        
        if user_input in ("1", "2", "3"):
            # Invalid command (no context available)
            display_error("Option not available in current context")
            return
        
        # Regular word/phrase lookup - treat multi-line input as single query
        # This resets the conversation as it's a new query
        self.conversation.reset()
        
        # Create selection data and process (keeping newlines intact)
        selection_data = SelectionData(
            selection=user_input,
            phrase="",
            paragraph="",
            file=""
        )
        self._process_selection(selection_data)

    def _handle_follow_up(self, question: str):
        """Handle follow-up question about the last result"""
        console.print()
        
        try:
            # Get conversation history with the new question
            messages = self.conversation.add_follow_up(question)
            
            # Call LLM with conversation history
            response = self.conversation_llm.client.chat.completions.create(
                model=self.conversation_llm.model,
                messages=messages,
                temperature=0.7,
            )
            
            answer = response.choices[0].message.content
            
            # Add response to conversation
            self.conversation.add_response(answer)
            
            # Display the answer
            console.print("[blue]Answer:[/blue]\n")
            console.print(f"{answer}\n")
            
        except Exception as e:
            logger.error(f"Error in follow-up conversation: {e}")
            display_error(f"Failed to get response: {e}")

    def _process_selection(self, data: SelectionData):
        """Process selection through data layer and display result"""
        if not data.selection:
            return

        logger.debug(f"Processing selection: {data.selection}")

        result = self.data_layer.lookup(data)
        if result is None:
            display_error("Failed to lookup or translate")
            return

        display_result(result)
        
        # Start conversation with this result for potential follow-ups
        result_text = self._format_result_for_conversation(result)
        self.conversation.start_conversation(data.selection, result_text)
    
    def _format_result_for_conversation(self, result) -> str:
        """Format result as text for conversation context"""
        from lookup_vim.models import WordResult, TranslationResult, ConjugationResult
        
        if isinstance(result, TranslationResult):
            return f"Translation: {result.translation}\nExplanations: {result.explanations}"
        elif isinstance(result, WordResult):
            definitions = "\n".join([f"- {d.definition}" for d in result.definitions[:3]])
            return f"Word: {result.word}\nDefinitions:\n{definitions}"
        elif isinstance(result, ConjugationResult):
            return f"Conjugation of: {result.redirected_to}\n{result.message}"
        else:
            return str(result)


def main():
    """Entry point for the main lookup service"""
    fifo_path = Path(FIFO_PATH)
    cache_type = os.environ.get("CACHE_TYPE", "csv")

    service = MainLookupService(fifo_path, cache_type)
    service.start()


if __name__ == "__main__":
    main()
