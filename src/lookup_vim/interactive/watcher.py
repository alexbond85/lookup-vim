"""Main watcher script with FIFO and console input"""

import json
import logging
import os
import select
import sys
from pathlib import Path

from lookup_vim.constants import FIFO_PATH
from lookup_vim.interactive.display import (
    console,
    display_error,
    display_greeting,
    display_prompt,
)
from lookup_vim.interactive.handler import InputHandler
from lookup_vim.interactive.history import HistoryLogger
from lookup_vim.interactive.history_viewer import display_history
from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.services.translation import TranslationService
from lookup_vim.translation.scrapers.lerobert import LeRobertScraper
from lookup_vim.translation.translators.openai_llm import OpenAILLM
from lookup_vim.translation.translators.prompts import TranslationPrompts
from lookup_vim.translation.translators.translator import Translator

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class SelectionData:
    """Container for selection data from JSON"""

    def __init__(self, selection: str, phrase: str = "", paragraph: str = ""):
        self.selection = selection
        self.phrase = phrase
        self.paragraph = paragraph


class InteractiveDictionaryWatcher:
    """Main application coordinating FIFO and console input"""

    def __init__(self, fifo_path: Path):
        self.fifo_path = fifo_path
        self.fifo = None

        # Current context for phrase/paragraph translation options
        self.current_phrase: str | None = None
        self.current_paragraph: str | None = None

        # Initialize services
        scraper = LeRobertScraper()
        dictionary_service = DictionaryService(scraper)

        # Initialize translation with DI: LLM -> Translator -> Service
        llm = OpenAILLM(model="gpt-5.1")
        prompts = TranslationPrompts.create(
            source_lang="French", target_lang="Russian"
        )
        translator = Translator(structured_llm=llm, prompts=prompts)
        translation_service = TranslationService(provider=translator)

        self.handler = InputHandler(dictionary_service, translation_service)

        # Initialize history logger
        self.history = HistoryLogger(console)

    def start(self):
        """Start the interactive watcher"""
        display_greeting()

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self._cleanup()
            self.history.save_session()

    def _open_fifo(self):
        """Create and open FIFO in non-blocking mode"""
        # Create FIFO if it doesn't exist
        if not self.fifo_path.exists():
            os.mkfifo(self.fifo_path)
            logger.info(f"Created FIFO at {self.fifo_path}")

        # Open in non-blocking mode so we can select() on it
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
        """Simple event loop: select on both stdin and FIFO"""
        self.fifo = self._open_fifo()
        print_prompt = True

        while True:
            # Display prompt when needed
            if print_prompt:
                has_context = bool(
                    self.current_phrase or self.current_paragraph
                )
                display_prompt(has_context)
                print_prompt = False

            # Wait for input from either stdin or FIFO
            try:
                ready, _, _ = select.select(
                    [sys.stdin, self.fifo], [], [], 1.0
                )
            except OSError:
                # Handle interrupted system call
                continue

            # Check FIFO for Vim selections
            if self.fifo in ready:
                try:
                    assert self.fifo is not None  # Type narrowing for mypy
                    line = self.fifo.readline().strip()
                    if line:
                        data = json.loads(line)
                        selection_data = SelectionData(
                            selection=data.get("selection", ""),
                            phrase=data.get("phrase", ""),
                            paragraph=data.get("paragraph", ""),
                        )
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
                        print("\n👋 Goodbye!")
                        break

                    # Process user input
                    self._process_user_input(user_input)

                except EOFError:
                    print("\n👋 Goodbye!")
                    break

    def _process_selection(self, data: SelectionData):
        """Process selection from FIFO"""
        if not data.selection:
            return

        logger.debug(f"Processing selection: {data.selection}")

        # Save context for options 1/2
        self.current_phrase = data.phrase or None
        self.current_paragraph = data.paragraph or None

        # Determine context for translation
        context = data.phrase if data.phrase else None

        # Process and display
        result = self.handler.process_input(data.selection, context)
        self.handler.display_result(result)

    def _process_user_input(self, user_input: str):
        """Process console input from user"""

        # Check for history command
        if user_input.lower() in ("h", "history"):
            display_history()
            return

        # Check for special commands
        if user_input == "1" and self.current_phrase:
            # Translate phrase
            result = self.handler.process_input(self.current_phrase)
            self.handler.display_result(result)
            return

        if user_input == "2" and self.current_paragraph:
            # Translate paragraph
            result = self.handler.process_input(self.current_paragraph)
            self.handler.display_result(result)
            return

        if user_input in ("1", "2"):
            # Invalid command (no context available)
            display_error("No phrase/paragraph context available")
            return

        # Regular word/phrase lookup
        result = self.handler.process_input(user_input)
        self.handler.display_result(result)


def main():
    """Entry point for the interactive dictionary watcher"""
    fifo_path = Path(FIFO_PATH)

    watcher = InteractiveDictionaryWatcher(fifo_path)
    watcher.start()


if __name__ == "__main__":
    main()
