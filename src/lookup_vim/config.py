"""Configuration loader for the application"""

import configparser
from dataclasses import dataclass
from pathlib import Path

# Project root: navigate from src/lookup_vim/ to root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default config path: config.ini in repository root
_CONFIG_PATH = PROJECT_ROOT / "config.ini"

# Cache directory (not configurable)
CACHE_DIR = PROJECT_ROOT / ".cache"
FIFO_PATH = CACHE_DIR / "nvim-selection.fifo"


@dataclass
class Config:
    """Application configuration"""

    fifo_path: str
    source_lang: str
    target_lang: str
    debug: bool


def load_config(path: Path | None = None) -> Config:
    """Load configuration from INI file"""
    config_path = path or _CONFIG_PATH
    parser = configparser.ConfigParser()

    if config_path.exists():
        parser.read(config_path)

    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    return Config(
        fifo_path=str(FIFO_PATH),
        source_lang=parser.get(
            "translation", "source_lang", fallback="French"
        ),
        target_lang=parser.get(
            "translation", "target_lang", fallback="Russian"
        ),
        debug=parser.getboolean("app", "debug", fallback=False),
    )
