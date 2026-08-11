#!/usr/bin/env python
"""YAML persistence for request class catalog entries (one file per class)."""

from __future__ import annotations

import contextlib
import hashlib
import os
from pathlib import Path

import yaml

from metagit.core.routing.models import RequestClass
from metagit.core.state.errors import StateConflictError

StateToken = str | None

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment,misc]


def _token_for_bytes(raw: bytes) -> StateToken:
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()


def _token_for_path(path: Path) -> StateToken:
    if not path.is_file():
        return None
    try:
        return _token_for_bytes(path.read_bytes())
    except OSError:
        return None


class ClassStore:
    """One-file-per-class YAML store with optimistic concurrency tokens."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def ensure_dirs(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)

    def path_for(self, class_id: str) -> Path:
        return self._root / f"{class_id}.yml"

    def load(self, class_id: str) -> tuple[RequestClass | None, StateToken]:
        path = self.path_for(class_id)
        token = _token_for_path(path)
        if not path.is_file():
            return None, token
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None, token
        return RequestClass.model_validate(raw), token

    def list(self) -> list[RequestClass]:
        if not self._root.is_dir():
            return []
        rows: list[RequestClass] = []
        for path in sorted(self._root.glob("*.yml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                rows.append(RequestClass.model_validate(raw))
        return rows

    def save(self, item: RequestClass, *, expected: StateToken) -> StateToken:
        path = self.path_for(item.id)
        self.ensure_dirs()
        with self._file_lock(path):
            current = _token_for_path(path)
            if current != expected:
                raise StateConflictError(
                    f"state conflict for {path.name}: expected token {expected!r}, found {current!r}",
                )
            payload = item.model_dump(mode="json", by_alias=True, exclude_none=True)
            text = yaml.safe_dump(payload, sort_keys=False)
            raw = text.encode("utf-8")
            path.write_bytes(raw)
            with contextlib.suppress(OSError):
                os.chmod(path, 0o600)
            return _token_for_bytes(raw)

    @contextlib.contextmanager
    def _file_lock(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None:
                with contextlib.suppress(OSError, AttributeError):
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    with contextlib.suppress(OSError, AttributeError):
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = ["ClassStore"]
