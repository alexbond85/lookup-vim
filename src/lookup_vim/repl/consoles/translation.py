"""Translation service console

Interactive REPL for testing LLM translations.

Usage:
    python -m lookup_vim.repl.consoles.translation
"""

from rich.console import Console

from lookup_vim.config import load_config
from lookup_vim.services.translation import TranslationService
from lookup_vim.translation.translators.openai_llm import OpenAILLM
from lookup_vim.translation.translators.prompts import TranslationPrompts
from lookup_vim.translation.translators.translator import Translator
from lookup_vim.repl.display import display_translation_result, display_error

console = Console()


def create_translation_service(
    source_lang: str | None = None,
    target_lang: str | None = None,
) -> TranslationService:
    """Create translation service with OpenAI LLM"""
    config = load_config()
    src = source_lang or config.source_lang
    tgt = target_lang or config.target_lang

    llm = OpenAILLM(model="gpt-5.1")
    prompts = TranslationPrompts.create(source_lang=src, target_lang=tgt)
    translator = Translator(structured_llm=llm, prompts=prompts)

    return TranslationService(provider=translator)


def main():
    """Translation console REPL"""
    config = load_config()
    service = create_translation_service()

    console.print("[cyan]🌐 Translation Console[/cyan]")
    console.print(f"[dim]{config.source_lang} → {config.target_lang}[/dim]\n")
    console.print("[dim]Enter text to translate. Use 'c:' prefix to add context.[/dim]")
    console.print("[dim]Example: c:La phrase complète. mot[/dim]\n")

    context: str | None = None

    while True:
        prompt = "[blue]text>[/blue] " if not context else f"[blue]text[/blue] [dim]({context[:20]}...)[/dim] "
        console.print(prompt, end="")

        try:
            line = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not line:
            continue

        if line.lower() in ("q", "quit", "exit"):
            break

        # Context command: "c:..." sets context
        if line.startswith("c:"):
            context = line[2:].strip()
            console.print(f"[dim]Context set: {context}[/dim]\n")
            continue

        # Clear context
        if line.lower() == "clear":
            context = None
            console.print("[dim]Context cleared[/dim]\n")
            continue

        try:
            result = service.translate(line, context)
            display_translation_result(result)
        except Exception as e:
            display_error(str(e))


if __name__ == "__main__":
    main()
