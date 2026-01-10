"""Configuration loader for the application"""

import configparser
from dataclasses import dataclass
from pathlib import Path

# Project root: navigate from src/lookup/ to root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default config path: config.ini in repository root
_CONFIG_PATH = PROJECT_ROOT / "config.ini"


@dataclass
class Config:
    """Application configuration"""

    cache_dir: Path
    fifo_path: Path
    selections_file: Path
    source_lang: str
    target_lang: str
    debug: bool


def load_config(path: Path | None = None) -> Config:
    """Load configuration from INI file (shared with Neovim plugin)"""
    config_path = path or _CONFIG_PATH
    parser = configparser.ConfigParser()

    if config_path.exists():
        parser.read(config_path)

    # Read paths from [paths] section (relative to project root)
    cache_dir = PROJECT_ROOT / parser.get("paths", "cache_dir", fallback=".cache")
    fifo_file = parser.get("paths", "fifo_file", fallback="nvim-selection.fifo")
    selections_file = parser.get("paths", "selections_file", fallback="selections.jsonl")

    # Ensure cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)

    return Config(
        cache_dir=cache_dir,
        fifo_path=cache_dir / fifo_file,
        selections_file=cache_dir / selections_file,
        source_lang=parser.get("translation", "source_lang", fallback="French"),
        target_lang=parser.get("translation", "target_lang", fallback="Russian"),
        debug=parser.getboolean("app", "debug", fallback=False),
    )
