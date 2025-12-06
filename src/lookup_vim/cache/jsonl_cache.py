import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from lookup_vim.cache.base import CacheBase
from lookup_vim.models import (
    ConjugationResult,
    Definition,
    SelectionData,
    TranslationResult,
    WordResult,
)


class JSONLCache(CacheBase):
    """JSONL-based persistent cache implementation with rich metadata"""

    def __init__(self):
        # .cache/selections.jsonl in project root
        # Navigate from src/lookup_vim/cache/ to project root
        project_root = Path(__file__).parent.parent.parent.parent
        self.cache_file = project_root / ".cache" / "selections.jsonl"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load cache from JSONL file"""
        if not self.cache_file.exists():
            return

        with open(self.cache_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    key = record.get("key")
                    if key:
                        self._cache[key] = record
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

    def _append(self, record: dict) -> None:
        """Append a record to the JSONL file"""
        with open(self.cache_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _serialize_result(self, result: Any) -> dict:
        """Convert result object to JSON-serializable dict"""
        if isinstance(result, WordResult):
            return {"_type": "WordResult", **asdict(result)}
        elif isinstance(result, ConjugationResult):
            return {"_type": "ConjugationResult", **asdict(result)}
        elif isinstance(result, TranslationResult):
            return {"_type": "TranslationResult", **asdict(result)}
        elif is_dataclass(result) and not isinstance(result, type):
            return {"_type": type(result).__name__, **asdict(result)}
        return result  # type: ignore[no-any-return]

    def _deserialize_result(self, data: Any) -> Any:
        """Convert dict back to result object"""
        if not isinstance(data, dict) or "_type" not in data:
            return data

        # Make a copy to avoid mutating the cached data
        data = data.copy()
        result_type = data.pop("_type")

        if result_type == "WordResult":
            # Convert definition dicts back to Definition objects
            data["definitions"] = [
                Definition(**d) if isinstance(d, dict) else d
                for d in data.get("definitions", [])
            ]
            return WordResult(**data)
        elif result_type == "ConjugationResult":
            return ConjugationResult(**data)
        elif result_type == "TranslationResult":
            return TranslationResult(**data)
        return data

    def get(self, key: str) -> Any | None:
        record = self._cache.get(key)
        if record:
            return self._deserialize_result(record.get("result"))
        return None

    def set(
        self, key: str, value: Any, context: SelectionData | None = None
    ) -> None:
        # Extract metadata
        timestamp = datetime.now().isoformat()
        book_name = ""
        line_number = None

        if context and context.file:
            # Extract book name from file path
            book_path = Path(context.file)
            if "books" in book_path.parts:
                book_name = book_path.stem
            else:
                book_name = book_path.name

        # Create record with rich metadata
        record = {
            "key": key,
            "selection": context.selection if context else "",
            "timestamp": timestamp,
            "book": book_name,
            "line_number": line_number,  # TODO: Add line tracking from Vim
            "context": {
                "selection": context.selection if context else "",
                "phrase": context.phrase if context else "",
                "paragraph": context.paragraph if context else "",
                "file": context.file if context else "",
            }
            if context
            else None,
            "result": self._serialize_result(value),
        }

        # Update in-memory cache
        self._cache[key] = record

        # Append to file
        self._append(record)

    def has(self, key: str) -> bool:
        return key in self._cache
