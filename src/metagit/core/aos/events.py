#!/usr/bin/env python
"""Append-only AOS lifecycle event store (RFC-0019)."""

from __future__ import annotations

import contextlib
import json
import uuid
from pathlib import Path
from typing import Any

from metagit.core.workspace.context_models import utc_now_iso

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment,misc]


class AosEventStore:
    """Persist AOS recovery/heartbeat events as JSONL under ``.metagit/events/``."""

    def __init__(self, session_root: str) -> None:
        root = Path(session_root).expanduser().resolve()
        self._path = root / ".metagit" / "events" / "aos.jsonl"

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | Exception:
        event = {
            "event_id": uuid.uuid4().hex,
            "type": event_type,
            "source": "aos",
            "at": utc_now_iso(),
            "payload": payload or {},
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event, sort_keys=True) + "\n"
            with self._path.open("a", encoding="utf-8") as handle:
                if fcntl is not None:
                    with contextlib.suppress(OSError, AttributeError):
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                handle.write(line)
                if fcntl is not None:
                    with contextlib.suppress(OSError, AttributeError):
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            return exc
        return event


__all__ = ["AosEventStore"]
