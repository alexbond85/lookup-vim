"""Translation service standalone interface

Interactive shell for testing LLM translations.

Usage:
    python -m robert.cli.repl.translation
"""

from rich.console import Console

from lookup.cli.display import display_error, display_translation_result
from lookup.cli.factory import ServiceFactory

console = Console()


def main():
    """Translation standalone shell"""
    factory = ServiceFactory()
    service = factory.translation_service

    console.print("[cyan]🌐 Translation[/cyan]")
    console.print(
        f"[dim]{factory.source_lang} → {factory.target_lang}[/dim]\n"
    )
    console.print(
        "[dim]Enter text to translate. Use 'c:' prefix to add context.[/dim]"
    )
    console.print("[dim]Example: c:La phrase complète. mot[/dim]\n")

    context: str | None = None

    while True:
        prompt = (
            "[blue]text>[/blue] "
            if not context
            else f"[blue]text[/blue] [dim]({context[:20]}...)[/dim] "
        )
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
