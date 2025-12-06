"""Dictionary service standalone interface

Interactive shell for testing LeRobert dictionary lookups.

Usage:
    python -m lookup_vim.cli.standalone.dictionary
"""

from rich.console import Console

from lookup_vim.cli.display import display_error, display_word_result
from lookup_vim.cli.factory import ServiceFactory

console = Console()


def main():
    """Dictionary standalone shell"""
    factory = ServiceFactory()
    service = factory.dictionary_service

    console.print("[cyan]📖 Dictionary[/cyan]")
    console.print("[dim]LeRobert dictionary lookups[/dim]\n")

    while True:
        console.print("[blue]word>[/blue] ", end="")
        try:
            word = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not word:
            continue

        if word.lower() in ("q", "quit", "exit"):
            break

        try:
            result = service.lookup_word(word)
            display_word_result(result)
        except ValueError:
            display_error(f"Not found: {word}")
        except Exception as e:
            display_error(str(e))


if __name__ == "__main__":
    main()
