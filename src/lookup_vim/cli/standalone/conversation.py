"""Conversation service standalone interface

Interactive shell for testing follow-up conversations with LLM.

Usage:
    python -m lookup_vim.cli.standalone.conversation
"""

from rich import box
from rich.console import Console
from rich.panel import Panel

from lookup_vim.cli.display import display_error
from lookup_vim.cli.factory import ServiceFactory

console = Console()


def main():
    """Conversation standalone shell"""
    factory = ServiceFactory()
    service = factory.conversation_service

    console.print("[cyan]💬 Conversation[/cyan]")
    console.print(
        f"[dim]Language learning assistant ({factory.source_lang} → {factory.target_lang})[/dim]\n"
    )
    console.print("[dim]Commands:[/dim]")
    console.print("[dim]  seed:<text>  - Set initial context (simulates lookup result)[/dim]")
    console.print("[dim]  reset       - Clear conversation[/dim]")
    console.print("[dim]  history     - Show message history[/dim]")
    console.print("[dim]  q/quit      - Exit[/dim]\n")

    while True:
        status = (
            "[green]active[/green]" if service.has_conversation() else "[dim]no context[/dim]"
        )
        console.print(f"[blue]>[/blue] [{status}] ", end="")

        try:
            line = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not line:
            continue

        if line.lower() in ("q", "quit", "exit"):
            break

        # Seed context (simulates having looked something up)
        if line.startswith("seed:"):
            seed_text = line[5:].strip()
            service.reset()
            service.add_assistant_message(seed_text)
            console.print(f"[dim]Context seeded with: {seed_text[:50]}...[/dim]\n")
            continue

        # Reset conversation
        if line.lower() == "reset":
            service.reset()
            console.print("[dim]Conversation reset[/dim]\n")
            continue

        # Show history
        if line.lower() == "history":
            if not service._messages:
                console.print("[dim]No messages yet[/dim]\n")
            else:
                for msg in service._messages:
                    role = msg["role"]
                    content = (
                        msg["content"][:100] + "..."
                        if len(msg["content"]) > 100
                        else msg["content"]
                    )
                    style = {"system": "yellow", "assistant": "cyan", "user": "green"}.get(
                        role, "white"
                    )
                    console.print(f"[{style}]{role}:[/{style}] {content}")
                console.print()
            continue

        # Check for context
        if not service.has_conversation():
            console.print(
                "[yellow]No context yet. Use 'seed:<text>' to set initial context.[/yellow]\n"
            )
            continue

        # Generate response
        try:
            response = service.generate_response(line)
            if response:
                console.print()
                console.print(
                    Panel(
                        response,
                        title="[cyan]Response[/cyan]",
                        box=box.ROUNDED,
                        border_style="cyan",
                    )
                )
                console.print()
            else:
                display_error("No response generated")
        except Exception as e:
            display_error(str(e))


if __name__ == "__main__":
    main()

