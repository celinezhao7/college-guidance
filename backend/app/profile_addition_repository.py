"""Replaceable persistence boundary for user-confirmed profile evidence."""

import json
import os
import tempfile
from pathlib import Path
from typing import Protocol


class ProfileAdditionRepository(Protocol):
    def load(self, profile_id: str) -> list[dict]: ...
    def write(self, profile_id: str, records: list[dict]) -> None: ...


class JsonProfileAdditionRepository:
    """Local single-instance implementation with atomic file replacement."""

    def __init__(self, directory: Path):
        self.directory = directory

    def _path(self, profile_id: str) -> Path:
        return self.directory / f"{profile_id}.json"

    def load(self, profile_id: str) -> list[dict]:
        path = self._path(profile_id)
        if not path.is_file():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def write(self, profile_id: str, records: list[dict]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(profile_id)
        fd, temporary = tempfile.mkstemp(dir=self.directory, suffix=".json.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(records, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
