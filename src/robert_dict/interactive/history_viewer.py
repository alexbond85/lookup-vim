"""History viewer for replaying saved dictionary sessions"""

import logging
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel

from robert_dict.interactive.history import HistoryLogger

logger = logging.getLogger(__name__)
console = Console()


def display_history(date_str: Optional[str] = None, history_dir: Optional[Path] = None):
    """
    Display history for a specific date with all colors preserved

    Args:
        date_str: Date string in YYYY-MM-DD format, or None for today
        history_dir: Directory containing history files
    """
    # Initialize logger to get file paths
    history_logger = HistoryLogger(console, history_dir)

    txt_path, html_path = history_logger.get_history_file(date_str)

    if txt_path is None or not txt_path.exists():
        if date_str:
            console.print(f"[yellow]No history found for {date_str}[/yellow]")
        else:
            console.print("[yellow]No history found for today[/yellow]")
        console.print("\nAvailable dates:")
        list_available_dates(history_dir)
        return

    # Display header
    display_name = date_str if date_str else "Today"
    header = Panel(
        f"[blue]History for {display_name}[/blue]", box=box.ROUNDED, border_style="blue"
    )
    console.print(header)
    console.print()

    # Read and display the text file (contains ANSI color codes)
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Print raw content - Rich will interpret ANSI codes
            print(content)
    except Exception as e:
        console.print(f"[red]Error reading history: {e}[/red]")
        return

    # Show footer with file locations
    console.print("\n" + "─" * 60)
    console.print(f"[dim]Text version: {txt_path}[/dim]")
    if html_path.exists():
        console.print(f"[dim]HTML version: {html_path}[/dim]")
        console.print(f"[dim]Open in browser: open {html_path}[/dim]")


def list_available_dates(history_dir: Optional[Path] = None):
    """
    List all available history dates

    Args:
        history_dir: Directory containing history files
    """
    history_logger = HistoryLogger(Console(), history_dir)
    dates = history_logger.list_available_dates()

    if not dates:
        console.print("[dim]No history files found[/dim]")
        return

    console.print("[blue]Available history dates:[/blue]")
    for date in dates:
        console.print(f"  • {date}")


def interactive_browse(history_dir: Optional[Path] = None):
    """
    Interactive mode to browse through history

    Args:
        history_dir: Directory containing history files
    """
    history_logger = HistoryLogger(Console(), history_dir)
    dates = history_logger.list_available_dates()

    if not dates:
        console.print("[yellow]No history found[/yellow]")
        return

    current_index = 0

    while True:
        console.clear()
        display_history(dates[current_index], history_dir)

        console.print(
            "\n[dim]Navigation: [n]ext | [p]revious | [q]uit | [date] Jump to date[/dim]"
        )
        console.print("[blue]>[/blue] ", end="")

        try:
            user_input = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input in ("q", "quit", "exit"):
            break
        elif user_input in ("n", "next"):
            if current_index < len(dates) - 1:
                current_index += 1
            else:
                console.print("[yellow]Already at oldest history[/yellow]")
                input("Press Enter to continue...")
        elif user_input in ("p", "prev", "previous"):
            if current_index > 0:
                current_index -= 1
            else:
                console.print("[yellow]Already at newest history[/yellow]")
                input("Press Enter to continue...")
        elif user_input in dates:
            current_index = dates.index(user_input)
        elif user_input:
            console.print(
                f"[yellow]Invalid command or date not found: {user_input}[/yellow]"
            )
            input("Press Enter to continue...")
