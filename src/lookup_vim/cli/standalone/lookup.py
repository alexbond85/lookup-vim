"""Lookup service standalone interface

Interactive shell for testing the full lookup chain (cache → dictionary → translation).

Usage:
    python -m lookup_vim.cli.standalone.lookup
"""

from rich.console import Console

from lookup_vim.cli.display import display_error, display_result
from lookup_vim.cli.factory import ServiceFactory
from lookup_vim.models import SelectionData

console = Console()


def main():
    """Lookup standalone shell"""
    factory = ServiceFactory()
    service = factory.lookup_service

    console.print("[cyan]🔍 Lookup[/cyan]")
    console.print(
        f"[dim]Chain: cache → dictionary → translation ({factory.source_lang} → {factory.target_lang})[/dim]\n"
    )
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

