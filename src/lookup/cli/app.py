"""Main CLI application - orchestrates lookups and conversations

This is the main entry point that orchestrates:
- Input sources (stdin, FIFO, etc.)
- LookupService for lookups
- ConversationService for follow-up conversations
- Display/output

Open/Closed: Add new input sources without modifying this code.
"""

import logging
import os

from lookup.cli.display import console, display_error, display_result
from lookup.cli.inputs import (
    InputEvent,
    InputMultiplexer,
    InputSource,
)
from lookup.conversation.service import ConversationService
from lookup.domain import (
    ConjugationResult,
    SelectionData,
    TranslationResult,
    WordResult,
)
from lookup.orchestration.service import LookupService

logger = logging.getLogger(__name__)

LookupResult = WordResult | ConjugationResult | TranslationResult | None


class LookupApp:
    """Main lookup application with pluggable input sources

    Uses composition to combine:
    - InputMultiplexer for input handling
    - LookupService for lookups
    - ConversationService for follow-up conversations
    - Display functions for output

    Add new input sources via add_source() without modifying this class.
    """

    def __init__(
        self,
        lookup_service: LookupService,
        conversation_service: ConversationService,
        sources: list[InputSource] | None = None,
    ):
        self._lookup_service = lookup_service
        self._conversation_service = conversation_service
        self._inputs = InputMultiplexer(sources or [])

        # Context from FIFO for phrase/paragraph translation
        self._current_phrase: str | None = None
        self._current_paragraph: str | None = None

    def add_source(self, source: InputSource) -> None:
        """Add an input source (Open for extension)"""
        self._inputs.add_source(source)

    def start(self):
        """Start the main loop"""
        source_names = [s.name for s in self._inputs.sources]
        console.print("[blue]Lookup[/blue]\n")
        console.print(f"[dim]Listening: {', '.join(source_names)}[/dim]\n")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n\nStopped")
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
                print("\nStopped")
                return

    def _display_prompt(self):
        """Display input prompt with available options"""
        options = []

        if self._current_phrase:
            options.append("[1] phrase")
        if self._current_paragraph:
            options.append("[2] paragraph")
        if self._conversation_service.has_conversation():
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

            if text == "?" and self._conversation_service.has_conversation():
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
        # Reset follow-up conversation for new lookup
        self._conversation_service.reset()

        result = self._lookup_service.lookup(data)
        if result is None:
            display_error("Failed to lookup or translate")
            return

        # Initialize follow-up conversation with result context
        result_text = self._format_result_for_conversation(
            data.selection, result
        )
        self._conversation_service.add_assistant_message(result_text)

        # Pass phrase context to display
        phrase = data.phrase if data.phrase else None
        display_result(result, phrase)

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

        answer = self._conversation_service.generate_response(question)
        if answer:
            console.print("[blue]Answer:[/blue]\n")
            console.print(f"{answer}\n")
        else:
            display_error("Failed to get response")

    def _format_result_for_conversation(
        self, query: str, result: LookupResult
    ) -> str:
        """Format result as text for conversation context"""
        if isinstance(result, TranslationResult):
            content = (
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
            content = f"Word: {result.word}\nDefinitions:\n{definitions}"
        elif isinstance(result, ConjugationResult):
            content = (
                f"Conjugation of: {result.redirected_to}\n{result.message}"
            )
        else:
            content = str(result) if result else ""

        return f"Query: {query}\nResult: {content}"


def main():
    """Entry point for the CLI"""
    import traceback

    from lookup.cli.factory import ServiceFactory

    cache_type = os.environ.get("CACHE_TYPE", "jsonl")
    factory = ServiceFactory(cache_type=cache_type)
    factory.setup_logging()

    try:
        app = factory.create_app()
        app.start()
    except Exception as e:
        if factory.debug:
            traceback.print_exc()
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
