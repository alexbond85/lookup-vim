"""CLI entry point for viewing dictionary history"""

import argparse
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

from rich.console import Console

from robert_dict.interactive.history import HistoryLogger
from robert_dict.interactive.history_viewer import (
    display_history,
    interactive_browse,
    list_available_dates,
)

console = Console()


def main():
    """Main entry point for robert-history command"""
    parser = argparse.ArgumentParser(
        description="View dictionary lookup history with preserved colors"
    )
    parser.add_argument(
        "date",
        nargs="?",
        help="Date to view history for (YYYY-MM-DD format). Defaults to today.",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all available history dates",
    )
    parser.add_argument(
        "--html", action="store_true", help="Open HTML version in browser"
    )
    parser.add_argument(
        "--browse",
        "-b",
        action="store_true",
        help="Interactive mode to browse through history",
    )
    parser.add_argument(
        "--dir", type=str, help="Custom history directory path"
    )

    args = parser.parse_args()

    # Determine history directory
    history_dir = Path(args.dir) if args.dir else None

    # Handle --list flag
    if args.list:
        list_available_dates(history_dir)
        return

    # Handle --browse flag
    if args.browse:
        interactive_browse(history_dir)
        return

    # Validate date format if provided
    date_str = args.date
    if date_str:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            console.print(
                f"[red]Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.[/red]"
            )
            sys.exit(1)

    # Handle --html flag
    if args.html:
        history_logger = HistoryLogger(Console(), history_dir)
        txt_path, html_path = history_logger.get_history_file(date_str)

        if html_path is None or not html_path.exists():
            if date_str:
                console.print(
                    f"[yellow]No HTML history found for {date_str}[/yellow]"
                )
            else:
                console.print(
                    "[yellow]No HTML history found for today[/yellow]"
                )
            sys.exit(1)

        console.print(f"[blue]Opening {html_path} in browser...[/blue]")
        webbrowser.open(f"file://{html_path.absolute()}")
        return

    # Display history for specified date (or today)
    display_history(date_str, history_dir)


if __name__ == "__main__":
    main()
