"""Constants used throughout the application"""

from enum import IntEnum


class ExitCode(IntEnum):
    """Exit codes for the CLI application"""
    SUCCESS = 0
    WORD_NOT_FOUND = 1
    GENERAL_ERROR = 2


# URL constants
BASE_URL = "https://dictionnaire.lerobert.com/definition"

# Default settings
DEFAULT_TIMEOUT = 10
DEFAULT_JSON_INDENT = 2

