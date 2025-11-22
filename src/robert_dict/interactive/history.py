"""History logging for dictionary lookups and translations"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

logger = logging.getLogger(__name__)


class HistoryLogger:
    """Logs all console output to daily history files"""

    def __init__(self, console: Console, history_dir: Optional[Path] = None):
        """
        Initialize history logger

        Args:
            console: Rich console instance to record from
            history_dir: Directory to save history files (defaults to ./history)
        """
        self.console = console

        # Set up history directory
        if history_dir is None:
            # Default to history/ in project root
            project_root = Path(__file__).parent.parent.parent.parent
            history_dir = project_root / "history"

        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(exist_ok=True)

        # Track current date for daily file rotation
        self.current_date = datetime.now().date()

        logger.debug(f"Initialized HistoryLogger with directory: {self.history_dir}")

    def _get_date_string(self, date=None) -> str:
        """Get date string in YYYY-MM-DD format"""
        if date is None:
            date = self.current_date
        return date.strftime("%Y-%m-%d")

    def _get_file_paths(self, date=None) -> tuple[Path, Path]:
        """Get paths for text and HTML history files for a date"""
        date_str = self._get_date_string(date)
        txt_path = self.history_dir / f"{date_str}.txt"
        html_path = self.history_dir / f"{date_str}.html"
        return txt_path, html_path

    def _check_date_rotation(self):
        """Check if date has changed and save/rotate if needed"""
        current = datetime.now().date()
        if current != self.current_date:
            # Date changed, save current session
            self.save_session()
            self.current_date = current

    def save_session(self):
        """Save current console recording to daily history files"""
        try:
            self._check_date_rotation()

            txt_path, html_path = self._get_file_paths()

            # Export in both formats
            # For text: preserve ANSI color codes
            self.console.save_text(str(txt_path), clear=False)

            # For HTML: create browsable version
            self.console.save_html(str(html_path), clear=False)

            logger.debug(f"Saved history to {txt_path} and {html_path}")

        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def get_history_file(
        self, date_str: Optional[str] = None
    ) -> tuple[Optional[Path], Optional[Path]]:
        """
        Get history file paths for a specific date

        Args:
            date_str: Date string in YYYY-MM-DD format, or None for today

        Returns:
            Tuple of (txt_path, html_path) or (None, None) if not found
        """
        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                txt_path, html_path = self._get_file_paths(date)
            except ValueError:
                logger.error(f"Invalid date format: {date_str}")
                return None, None
        else:
            txt_path, html_path = self._get_file_paths()

        # Check if at least one file exists
        if txt_path.exists() or html_path.exists():
            return txt_path, html_path

        return None, None

    def list_available_dates(self) -> list[str]:
        """
        List all dates that have history files

        Returns:
            List of date strings in YYYY-MM-DD format, sorted newest first
        """
        dates = set()

        # Find all .txt files in history directory
        for file_path in self.history_dir.glob("*.txt"):
            date_str = file_path.stem  # Remove .txt extension
            try:
                # Validate it's a proper date
                datetime.strptime(date_str, "%Y-%m-%d")
                dates.add(date_str)
            except ValueError:
                continue

        # Sort newest first
        return sorted(dates, reverse=True)
