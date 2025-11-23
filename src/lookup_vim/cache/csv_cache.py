import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from lookup_vim.cache.base import CacheBase
from lookup_vim.models import SelectionData


class CSVCache(CacheBase):
    """CSV-based persistent cache implementation with context tracking"""

    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "robert-online"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = cache_dir / "cache.csv"
        self._cache: dict[str, Any] = {}
        self._contexts: dict[str, SelectionData | None] = {}
        self._load()

    def _load(self) -> None:
        """Load cache from CSV file"""
        if not self.cache_file.exists():
            return

        with open(self.cache_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row["key"]
                context_json = row.get("context", "")
                result_json = row["result_json"]

                self._cache[key] = json.loads(result_json)
                if context_json:
                    context_data = json.loads(context_json)
                    self._contexts[key] = SelectionData(**context_data)
                else:
                    self._contexts[key] = None

    def _save(self) -> None:
        """Save cache to CSV file"""
        with open(self.cache_file, "w", encoding="utf-8", newline="") as f:
            fieldnames = ["key", "context", "result_json"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for key, value in self._cache.items():
                context_data = self._contexts.get(key)
                context_json = (
                    json.dumps(asdict(context_data), ensure_ascii=False) if context_data else ""
                )
                writer.writerow(
                    {
                        "key": key,
                        "context": context_json,
                        "result_json": json.dumps(value, ensure_ascii=False),
                    }
                )

    def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    def set(
        self, key: str, value: Any, context: SelectionData | None = None
    ) -> None:
        self._cache[key] = value
        self._contexts[key] = context
        self._save()

    def has(self, key: str) -> bool:
        return key in self._cache
