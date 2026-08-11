#!/usr/bin/env python
"""YAML persistence for routing run records (one file per run)."""

from __future__ import annotations

import contextlib
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from metagit.core.routing.models import Run, RunDispatch, Tier
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


def _utc_now_iso(now_fn: Callable[[], datetime] | None = None) -> str:
    now = now_fn() if now_fn is not None else datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_id(class_id: str, opened_iso: str) -> str:
    stamp = opened_iso.replace("-", "").replace(":", "")
    date_part = stamp[0:8]
    time_part = stamp[9:15]
    return f"RUN-{date_part}-{time_part}-{class_id}"


def open_run_for(
    class_id: str,
    *,
    tier: Tier,
    actor: str,
    lane: str | None = None,
    objective: str | None = None,
    dispatch: RunDispatch | None = None,
    now_fn: Callable[[], datetime] | None = None,
) -> Run:
    """Create an open run record for one class."""
    opened = _utc_now_iso(now_fn)
    return Run(
        id=_run_id(class_id, opened),
        **{"class": class_id},
        tier=tier,
        lane=lane,
        actor=actor,
        objective=objective,
        dispatch=dispatch or RunDispatch(),
        opened=opened,
    )


class RunStore:
    """One-file-per-run YAML store with optimistic concurrency tokens."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def ensure_dirs(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
        return self._root / f"{run_id}.yml"

    def load(self, run_id: str) -> tuple[Run | None, StateToken]:
        path = self.path_for(run_id)
        token = _token_for_path(path)
        if not path.is_file():
            return None, token
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None, token
        return Run.model_validate(raw), token

    def list(self) -> list[Run]:
        if not self._root.is_dir():
            return []
        rows: list[Run] = []
        for path in sorted(self._root.glob("RUN-*.yml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                rows.append(Run.model_validate(raw))
        return rows

    def list_for_class(self, class_id: str) -> list[Run]:
        return [row for row in self.list() if row.cls == class_id]

    def save(self, item: Run, *, expected: StateToken) -> StateToken:
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


__all__ = ["RunStore", "open_run_for"]
