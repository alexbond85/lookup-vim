"""Lookup service console

Interactive REPL for testing the full lookup chain (cache → dictionary → translation).

Usage:
    python -m lookup_vim.repl.consoles.lookup
"""

from rich.console import Console

from lookup_vim.cache import create_cache
from lookup_vim.config import load_config
from lookup_vim.models import SelectionData
from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.services.lookup import LookupService
from lookup_vim.services.translation import TranslationService
from lookup_vim.translation.scrapers.lerobert import LeRobertScraper
from lookup_vim.translation.translators.openai_llm import OpenAILLM
from lookup_vim.translation.translators.prompts import TranslationPrompts
from lookup_vim.translation.translators.translator import Translator
from lookup_vim.repl.display import display_result, display_error

console = Console()


def create_lookup_service(
    cache_type: str = "memory",
    source_lang: str | None = None,
    target_lang: str | None = None,
) -> LookupService:
    """Create lookup service with all dependencies"""
    config = load_config()
    src = source_lang or config.source_lang
    tgt = target_lang or config.target_lang

    cache = create_cache(cache_type)

    # Translation service
    llm = OpenAILLM(model="gpt-5.1")
    prompts = TranslationPrompts.create(source_lang=src, target_lang=tgt)
    translator = Translator(structured_llm=llm, prompts=prompts)
    translation_service = TranslationService(provider=translator)

    # Dictionary service
    scraper = LeRobertScraper()
    dictionary_service = DictionaryService(scraper)

    # Lookup service with dictionary
    return LookupService(cache, translation_service).with_dictionary(dictionary_service)


def main():
    """Lookup console REPL"""
    config = load_config()
    service = create_lookup_service()

    console.print("[cyan]🔍 Lookup Console[/cyan]")
    console.print(f"[dim]Chain: cache → dictionary → translation ({config.source_lang} → {config.target_lang})[/dim]\n")
    console.print("[dim]Commands:[/dim]")
    console.print("[dim]  <text>           - Auto lookup (chain)[/dim]")
    console.print("[dim]  d:<word>         - Force dictionary lookup[/dim]")
    console.print("[dim]  t:<text>         - Force translation[/dim]")
    console.print("[dim]  ctx:<phrase>     - Set context phrase[/dim]")
    console.print("[dim]  clear            - Clear context[/dim]")
    console.print("[dim]  q/quit           - Exit[/dim]\n")

    context_phrase: str = ""

    while True:
        ctx_hint = f" [dim]({context_phrase[:20]}...)[/dim]" if context_phrase else ""
        console.print(f"[blue]lookup>{ctx_hint}[/blue] ", end="")

        try:
            line = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not line:
            continue

        if line.lower() in ("q", "quit", "exit"):
            break

        # Set context
        if line.startswith("ctx:"):
            context_phrase = line[4:].strip()
            console.print(f"[dim]Context set: {context_phrase}[/dim]\n")
            continue

        # Clear context
        if line.lower() == "clear":
            context_phrase = ""
            console.print("[dim]Context cleared[/dim]\n")
            continue

        # Determine handler and text
        handler: str | None = None
        text = line

        if line.startswith("d:"):
            handler = "dictionary"
            text = line[2:].strip()
        elif line.startswith("t:"):
            handler = "translation"
            text = line[2:].strip()

        if not text:
            continue

        selection_data = SelectionData(
            selection=text,
            phrase=context_phrase,
            paragraph="",
            file="",
        )

        try:
            result = service.lookup(selection_data, handler=handler)
            if result:
                display_result(result)
            else:
                display_error("No result")
        except ValueError as e:
            display_error(str(e))
        except Exception as e:
            display_error(str(e))


if __name__ == "__main__":
    main()

