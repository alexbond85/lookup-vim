"""Main watcher script with file monitoring and console input"""

import json
import logging
import select
import sys
import time
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver

from robert_dict.interactive.display import (
    console,
    display_error,
    display_greeting,
    display_prompt,
)
from robert_dict.interactive.handler import InputHandler
from robert_dict.interactive.history import HistoryLogger
from robert_dict.interactive.history_viewer import display_history
from robert_dict.scrapers.lerobert import LeRobertScraper
from robert_dict.services.dictionary import DictionaryService
from robert_dict.services.translation import ChatGPTTranslationService

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class SelectionData:
    """Container for selection data from JSON file"""

    def __init__(self, selection: str, phrase: str = "", paragraph: str = ""):
        self.selection = selection
        self.phrase = phrase
        self.paragraph = paragraph


class SelectionFileHandler(FileSystemEventHandler):
    """Handles file modification events for selection.json"""

    def __init__(self, file_path: Path, change_queue: Queue):
        self.file_path = file_path
        self.change_queue = change_queue
        self.last_modified: float = 0.0

    def on_modified(self, event):
        """Handle file modification event"""
        # Convert both to absolute paths for comparison
        event_path = str(Path(event.src_path).resolve())
        target_path = str(self.file_path.resolve())

        if event_path != target_path:
            return

        # Debounce: avoid duplicate events
        current_time = time.time()
        if current_time - self.last_modified < 0.5:
            return
        self.last_modified = current_time

        try:
            data = self._read_selection_file()
            if data:
                self.change_queue.put(data)
                logger.debug(f"File changed, added to queue: {data.selection}")
        except Exception as e:
            logger.error(f"Error reading selection file: {e}")

    def _read_selection_file(self) -> SelectionData | None:
        """Read and parse selection.json file"""
        try:
            # Small delay to ensure file write is complete
            time.sleep(0.1)

            with open(self.file_path, encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return None
                data = json.loads(content)

            selection = data.get("selection", "").strip()
            phrase = data.get("phrase", "").strip()
            paragraph = data.get("paragraph", "").strip()

            if not selection:
                return None

            return SelectionData(selection, phrase, paragraph)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.debug(f"Could not parse selection file: {e}")
            return None


class InteractiveDictionaryWatcher:
    """Main application coordinating file watching and console input"""

    def __init__(self, selection_file: Path):
        self.selection_file = selection_file
        self.change_queue: Queue[SelectionData] = Queue()
        self.observer: BaseObserver | None = None

        # Current context for phrase/paragraph translation options
        self.current_phrase: str | None = None
        self.current_paragraph: str | None = None

        # Initialize services
        scraper = LeRobertScraper()
        dictionary_service = DictionaryService(scraper)
        translation_service = ChatGPTTranslationService()
        self.handler = InputHandler(dictionary_service, translation_service)

        # Initialize history logger
        self.history = HistoryLogger(console)

    def start(self):
        """Start the interactive watcher"""
        display_greeting()

        # Start file watcher
        self._start_file_watcher()

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self._stop_file_watcher()
            self.history.save_session()

    def _start_file_watcher(self):
        """Start watchdog observer for file monitoring"""
        event_handler = SelectionFileHandler(
            self.selection_file, self.change_queue
        )
        self.observer = Observer()
        self.observer.schedule(
            event_handler, str(self.selection_file.parent), recursive=False
        )
        self.observer.start()
        logger.debug("File watcher started")

    def _stop_file_watcher(self):
        """Stop watchdog observer"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.debug("File watcher stopped")

    def _main_loop(self):
        """Main event loop: check for file changes and process console input"""
        print_prompt = True

        while True:
            # Check for pending file changes
            if self._check_and_process_file_changes():
                # Something was processed, print prompt again
                print_prompt = True

            # Display prompt only when needed
            if print_prompt:
                has_context = bool(
                    self.current_phrase or self.current_paragraph
                )
                display_prompt(has_context)
                print_prompt = False

            # Non-blocking input: wait for input with timeout to check file changes
            user_input = self._get_input_with_timeout(timeout=0.5)

            if user_input is None:
                # Timeout, no input - check for file changes and loop
                continue

            # Got input, will need to print prompt again after processing
            print_prompt = True

            if user_input == "":
                # Empty input, just continue
                continue

            # Check for exit command
            if user_input.lower() in ("q", "quit", "exit"):
                print("\n👋 Goodbye!")
                break

            # Process user input
            self._process_user_input(user_input)

    def _get_input_with_timeout(self, timeout: float) -> str | None:
        """Get user input with a timeout, returns None if timeout"""
        # Check if input is available (Unix only)
        if sys.platform != "win32":
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if ready:
                try:
                    return input().strip()
                except EOFError:
                    return "exit"
            return None
        else:
            # Windows: fallback to blocking input
            try:
                return input().strip()
            except EOFError:
                return "exit"

    def _check_and_process_file_changes(self) -> bool:
        """Check queue for pending file changes and process them

        Returns:
            bool: True if any changes were processed
        """
        try:
            # Non-blocking check
            processed = 0
            while not self.change_queue.empty():
                selection_data = self.change_queue.get_nowait()
                self._process_selection(selection_data)
                processed += 1
            return processed > 0
        except Empty:
            return False

    def _process_selection(self, data: SelectionData):
        """Process selection from file change"""
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
    # Determine selection file path
    # Use path relative to the script or from environment/config
    selection_file = (
        Path(__file__).parent.parent.parent.parent / "tmp" / "selection.json"
    )

    if not selection_file.parent.exists():
        print(f"Error: Directory {selection_file.parent} does not exist")
        sys.exit(1)

    # Create empty file if it doesn't exist
    if not selection_file.exists():
        selection_file.write_text(
            '{"selection": "", "phrase": "", "paragraph": ""}'
        )
        logger.info(f"Created selection file: {selection_file}")

    watcher = InteractiveDictionaryWatcher(selection_file)
    watcher.start()


if __name__ == "__main__":
    main()
