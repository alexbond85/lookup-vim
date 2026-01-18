"""Configuration loader for the application

Supports two modes:
1. Development mode: Uses repo-local config.ini and .cache directory
2. Production mode: Uses OS-specific app data directory (~/Library/Application Support/VimLookup on macOS)
"""

from __future__ import annotations

import configparser
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import platformdirs

APP_NAME = "VimLookup"
MAX_RECENT_FILES = 20

# Project root: navigate from src/lookup/ to root (for dev mode)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default config path: config.ini in repository root (for dev mode)
_CONFIG_PATH = PROJECT_ROOT / "config.ini"


def get_app_data_dir() -> Path:
    """Get the OS-specific app data directory"""
    return Path(platformdirs.user_data_dir(APP_NAME))


@dataclass
class Config:
    """Application configuration"""

    cache_dir: Path
    fifo_path: Path
    selections_file: Path
    source_lang: str
    target_lang: str
    debug: bool


def _load_settings_json(data_dir: Path) -> dict:
    """Load settings from JSON file in app data directory"""
    settings_file = data_dir / "settings.json"
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_settings_json(data_dir: Path, settings: dict) -> None:
    """Save settings to JSON file in app data directory"""
    data_dir.mkdir(parents=True, exist_ok=True)
    settings_file = data_dir / "settings.json"
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def load_config(path: Path | None = None, production: bool = False) -> Config:
    """Load configuration

    Args:
        path: Optional custom config file path (INI format, for dev mode)
        production: If True, use OS app data directory instead of repo

    In production mode:
        - Data stored in ~/Library/Application Support/VimLookup (macOS)
        - Settings stored in settings.json

    In development mode:
        - Data stored in .cache directory relative to repo
        - Settings in config.ini
    """
    if production:
        # Production mode: use OS-specific app data directory
        data_dir = get_app_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)

        # Load settings from JSON
        settings = _load_settings_json(data_dir)

        return Config(
            cache_dir=data_dir,
            fifo_path=data_dir / "nvim-selection.fifo",
            selections_file=data_dir / "selections.jsonl",
            source_lang=settings.get("source_lang", "French"),
            target_lang=settings.get("target_lang", "Russian"),
            debug=settings.get("debug", False),
        )

    # Development mode: use repo-local config.ini
    config_path = path or _CONFIG_PATH
    parser = configparser.ConfigParser()

    if config_path.exists():
        parser.read(config_path)

    # Read paths from [paths] section (relative to project root)
    cache_dir = PROJECT_ROOT / parser.get("paths", "cache_dir", fallback=".cache")
    fifo_file = parser.get("paths", "fifo_file", fallback="nvim-selection.fifo")
    selections_file = parser.get(
        "paths", "selections_file", fallback="selections.jsonl"
    )

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


def save_config(config: Config, production: bool = False) -> None:
    """Save configuration

    Args:
        config: Configuration to save
        production: If True, save to OS app data directory
    """
    if production:
        data_dir = get_app_data_dir()
        settings = {
            "source_lang": config.source_lang,
            "target_lang": config.target_lang,
            "debug": config.debug,
        }
        _save_settings_json(data_dir, settings)
    else:
        # Save to INI file in repo
        parser = configparser.ConfigParser()
        config_path = _CONFIG_PATH

        if config_path.exists():
            parser.read(config_path)

        if "translation" not in parser:
            parser["translation"] = {}

        parser["translation"]["source_lang"] = config.source_lang
        parser["translation"]["target_lang"] = config.target_lang

        with open(config_path, "w") as f:
            parser.write(f)


# --- Recent Files ---


@dataclass
class RecentFile:
    """A recently opened file"""
    path: str
    name: str
    last_opened: str  # ISO format datetime


def _get_recent_files_path(data_dir: Path) -> Path:
    """Get path to recent files JSON"""
    return data_dir / "recent_files.json"


def get_recent_files(data_dir: Path) -> list[RecentFile]:
    """Load list of recently opened files"""
    recent_file = _get_recent_files_path(data_dir)
    if not recent_file.exists():
        return []

    try:
        with open(recent_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [
                RecentFile(
                    path=item["path"],
                    name=item["name"],
                    last_opened=item["last_opened"]
                )
                for item in data
            ]
    except Exception:
        return []


def add_recent_file(data_dir: Path, file_path: str) -> list[RecentFile]:
    """Add a file to the recent files list

    Moves file to front if already present, limits to MAX_RECENT_FILES.
    Returns updated list.
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    # Load existing
    recent = get_recent_files(data_dir)

    # Remove if already present
    recent = [r for r in recent if r.path != file_path]

    # Add to front
    new_entry = RecentFile(
        path=file_path,
        name=Path(file_path).name,
        last_opened=datetime.now().isoformat()
    )
    recent.insert(0, new_entry)

    # Limit size
    recent = recent[:MAX_RECENT_FILES]

    # Save
    _save_recent_files(data_dir, recent)

    return recent


def _save_recent_files(data_dir: Path, recent: list[RecentFile]) -> None:
    """Save recent files list to disk"""
    recent_file = _get_recent_files_path(data_dir)
    data = [
        {"path": r.path, "name": r.name, "last_opened": r.last_opened}
        for r in recent
    ]
    with open(recent_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
