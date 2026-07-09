#!/usr/bin/env python
"""Local JSON list persistence with advisory file locks for ACL state."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment,misc]

T = TypeVar("T", bound=BaseModel)


class JsonListStore(Generic[T]):
    """Load and save a JSON object containing a named list of models."""

    def __init__(
        self,
        path: Path,
        *,
        key: str,
        model: type[T],
    ) -> None:
        self._path = path
        self._key = key
        self._model = model

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> list[T] | Exception:
        try:
            if not self._path.is_file():
                return []
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return []
            items = raw.get(self._key)
            if not isinstance(items, list):
                return []
            rows: list[T] = []
            for item in items:
                if isinstance(item, dict):
                    rows.append(self._model.model_validate(item))
            return rows
        except Exception as exc:  # noqa: BLE001 — surface load failures to callers
            return exc

    def save(self, rows: list[T]) -> None | Exception:
        try:
            with self._file_lock():
                payload = {self._key: [row.model_dump(mode="json") for row in rows]}
                self._path.parent.mkdir(parents=True, exist_ok=True)
                serialized = json.dumps(payload, indent=2) + "\n"
                self._path.write_text(serialized, encoding="utf-8")
                with contextlib.suppress(OSError):
                    os.chmod(self._path, 0o600)
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    def update(self, mutator: Callable[[list[T]], list[T]]) -> list[T] | Exception:
        """Load, mutate, and save under the file lock."""
        try:
            with self._file_lock():
                loaded = self._load_unlocked()
                if isinstance(loaded, Exception):
                    return loaded
                updated = mutator(loaded)
                payload = {self._key: [row.model_dump(mode="json") for row in updated]}
                self._path.parent.mkdir(parents=True, exist_ok=True)
                serialized = json.dumps(payload, indent=2) + "\n"
                self._path.write_text(serialized, encoding="utf-8")
                with contextlib.suppress(OSError):
                    os.chmod(self._path, 0o600)
                return updated
        except Exception as exc:  # noqa: BLE001
            return exc

    def _load_unlocked(self) -> list[T] | Exception:
        try:
            if not self._path.is_file():
                return []
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return []
            items = raw.get(self._key)
            if not isinstance(items, list):
                return []
            rows: list[T] = []
            for item in items:
                if isinstance(item, dict):
                    rows.append(self._model.model_validate(item))
            return rows
        except Exception as exc:  # noqa: BLE001
            return exc

    @contextlib.contextmanager
    def _file_lock(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            with contextlib.suppress(OSError, AttributeError):
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                with contextlib.suppress(OSError, AttributeError):
                    if fcntl is not None:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = ["JsonListStore"]
