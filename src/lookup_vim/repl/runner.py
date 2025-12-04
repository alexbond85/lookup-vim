"""REPL runner - ties inputs to the lookup engine

This is the main entry point that orchestrates:
- Input sources (stdin, FIFO, etc.)
- Core lookup engine
- Display/output

Open/Closed: Add new input sources without modifying this code.
"""

import logging
import os

from lookup_vim.config import get_config
from lookup_vim.models import SelectionData
from lookup_vim.repl.core import LookupEngine
from lookup_vim.repl.display import console, display_error, display_result
from lookup_vim.repl.inputs import (
    FifoSource,
    InputEvent,
    InputMultiplexer,
    InputSource,
    StdinSource,
)

logger = logging.getLogger(__name__)


class ReplRunner:
    """REPL runner with pluggable input sources

    Uses composition to combine:
    - InputMultiplexer for input handling
    - LookupEngine for core logic
    - Display functions for output

    Add new input sources via add_source() without modifying this class.
    """

    def __init__(
        self,
        engine: LookupEngine,
        sources: list[InputSource] | None = None,
    ):
        self._engine = engine
        self._inputs = InputMultiplexer(sources or [])

        # Context from FIFO for phrase/paragraph translation
        self._current_phrase: str | None = None
        self._current_paragraph: str | None = None

    def add_source(self, source: InputSource) -> None:
        """Add an input source (Open for extension)"""
        self._inputs.add_source(source)

    def start(self):
        """Start the REPL loop"""
        source_names = [s.name for s in self._inputs.sources]
        console.print("[blue]Robert Lookup REPL[/blue]\n")
        console.print(f"[dim]Listening: {', '.join(source_names)}[/dim]\n")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n\nREPL stopped")
        finally:
            self._inputs.close()

    def _main_loop(self):
        """Main event loop"""
        print_prompt = True

        while True:
            if print_prompt:
                self._display_prompt()
                print_prompt = False

            event = self._inputs.wait_for_input(timeout=0.5)
            if event is None:
                continue

            print_prompt = True

            # Handle the event
            should_exit = self._handle_event(event)
            if should_exit:
                print("\nREPL stopped")
                return

    def _display_prompt(self):
        """Display input prompt with available options"""
        options = []

        if self._current_phrase:
            options.append("[1] phrase")
        if self._current_paragraph:
            options.append("[2] paragraph")
        if self._engine.conversation.has_conversation():
            options.append("[?] follow-up")

        if options:
            options.append("[q] quit")
            console.print(f"[dim]{' | '.join(options)}[/dim]")
        else:
            console.print("[dim]Enter word/phrase | [q] quit[/dim]")

        console.print("[blue]>[/blue] ", end="")

    def _handle_event(self, event: InputEvent) -> bool:
        """Handle an input event

        Returns:
            True if should exit, False otherwise
        """
        text = event.text.strip()

        if not text:
            return False

        # Exit commands
        if text.lower() in ("q", "quit", "exit"):
            return True

        # Special commands (stdin only)
        if event.source == "stdin":
            if text == "1" and self._current_phrase:
                self._lookup_text(self._current_phrase)
                return False

            if text == "2" and self._current_paragraph:
                self._lookup_text(self._current_paragraph)
                return False

            if text == "?" and self._engine.conversation.has_conversation():
                self._handle_follow_up()
                return False

        # FIFO events have rich metadata
        if event.source == "fifo" and event.metadata:
            self._current_phrase = event.metadata.get("phrase") or None
            self._current_paragraph = event.metadata.get("paragraph") or None

            selection_data = SelectionData(
                selection=event.metadata.get("selection", ""),
                phrase=event.metadata.get("phrase", ""),
                paragraph=event.metadata.get("paragraph", ""),
                file=event.metadata.get("file", ""),
            )
            self._process_lookup(selection_data)
            return False

        # Regular text lookup
        self._lookup_text(text)
        return False

    def _lookup_text(self, text: str):
        """Lookup plain text (no context)"""
        selection_data = SelectionData(
            selection=text, phrase="", paragraph="", file=""
        )
        self._process_lookup(selection_data)

    def _process_lookup(self, data: SelectionData):
        """Process a lookup request"""
        result = self._engine.lookup(data)
        if result is None:
            display_error("Failed to lookup or translate")
            return

        display_result(result)

    def _handle_follow_up(self):
        """Handle follow-up question flow"""
        console.print("[dim]Follow-up question:[/dim]")
        console.print("[blue]>[/blue] ", end="")

        # Wait for the question (blocking on stdin)
        event = self._inputs.wait_for_input(timeout=30.0)
        if event is None or not event.text.strip():
            return

        question = event.text.strip()
        console.print()

        answer = self._engine.follow_up(question)
        if answer:
            console.print("[blue]Answer:[/blue]\n")
            console.print(f"{answer}\n")
        else:
            display_error("Failed to get response")


def create_default_runner(
    cache_type: str = "memory",
    source_lang: str | None = None,
    target_lang: str | None = None,
    enable_stdin: bool = True,
    enable_fifo: bool = True,
    fifo_path: str | None = None,
) -> ReplRunner:
    """Factory function to create a runner with default configuration

    Args:
        cache_type: Cache backend ("memory" or "jsonl")
        source_lang: Source language for translations (from config.ini if None)
        target_lang: Target language for translations (from config.ini if None)
        enable_stdin: Enable stdin input
        enable_fifo: Enable FIFO input from Vim
        fifo_path: Path to FIFO file (from config.ini if None)

    Returns:
        Configured ReplRunner
    """
    config = get_config()

    engine = LookupEngine(
        cache_type=cache_type,
        source_lang=source_lang or config.source_lang,
        target_lang=target_lang or config.target_lang,
    )

    sources: list[InputSource] = []
    if enable_stdin:
        sources.append(StdinSource())
    if enable_fifo:
        sources.append(FifoSource(fifo_path or config.fifo_path))

    return ReplRunner(engine=engine, sources=sources)


def main():
    """Entry point for the REPL"""
    logging.basicConfig(level=logging.WARNING)

    cache_type = os.environ.get("CACHE_TYPE", "jsonl")
    runner = create_default_runner(cache_type=cache_type)
    runner.start()


if __name__ == "__main__":
    main()
