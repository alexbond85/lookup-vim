"""Dictionary service console

Interactive REPL for testing LeRobert dictionary lookups.

Usage:
    python -m lookup_vim.repl.consoles.dictionary
"""

from rich.console import Console

from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.translation.scrapers.lerobert import LeRobertScraper
from lookup_vim.repl.display import display_word_result, display_error

console = Console()


def create_dictionary_service() -> DictionaryService:
    """Create dictionary service with LeRobert scraper"""
    scraper = LeRobertScraper()
    return DictionaryService(scraper)


def main():
    """Dictionary console REPL"""
    service = create_dictionary_service()

    console.print("[cyan]📖 Dictionary Console[/cyan]")
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
        except ValueError as e:
            display_error(f"Not found: {word}")
        except Exception as e:
            display_error(str(e))


if __name__ == "__main__":
    main()

