"""Configuration loader for the application"""

import configparser
from dataclasses import dataclass
from pathlib import Path

# Default config path: config.ini in repository root
_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.ini"

# Defaults if config.ini is missing
_DEFAULTS = {
    "fifo_path": "/tmp/nvim-selection.fifo",
    "source_lang": "French",
    "target_lang": "Russian",
}


@dataclass
class Config:
    """Application configuration"""

    fifo_path: str
    source_lang: str
    target_lang: str


def load_config(path: Path | None = None) -> Config:
    """Load configuration from INI file

    Args:
        path: Path to config file, defaults to config.ini in repo root

    Returns:
        Config with values from file or defaults
    """
    config_path = path or _CONFIG_PATH
    parser = configparser.ConfigParser()

    if config_path.exists():
        parser.read(config_path)

    return Config(
        fifo_path=parser.get("fifo", "path", fallback=_DEFAULTS["fifo_path"]),
        source_lang=parser.get(
            "translation", "source_lang", fallback=_DEFAULTS["source_lang"]
        ),
        target_lang=parser.get(
            "translation", "target_lang", fallback=_DEFAULTS["target_lang"]
        ),
    )


# Singleton instance
_config: Config | None = None


def get_config() -> Config:
    """Get or create the singleton config instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config
