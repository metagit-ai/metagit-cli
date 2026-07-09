#!/usr/bin/env python
"""Append-only merge orchestrator lifecycle event store."""

from __future__ import annotations

import contextlib
import json
import uuid
from pathlib import Path

from metagit.core.merge.models import MergeEvent, MergeEventType
from metagit.core.merge.paths import events_file
from metagit.core.workspace.context_models import utc_now_iso

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment,misc]


class MergeEventStore:
    """Persist typed merge orchestrator events as JSONL under ``.metagit/events/``."""

    def __init__(self, session_root: str) -> None:
        self._path = events_file(session_root)

    @property
    def path(self) -> Path:
        return self._path

    def append(
        self,
        event_type: MergeEventType,
        payload: dict | None = None,
        *,
        at: str | None = None,
    ) -> MergeEvent | Exception:
        event = MergeEvent(
            event_id=uuid.uuid4().hex,
            type=event_type,
            at=at or utc_now_iso(),
            payload=dict(payload or {}),
        )
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event.model_dump(mode="json"), sort_keys=False) + "\n"
            with self._path.open("a+", encoding="utf-8") as handle:
                if fcntl is not None:
                    with contextlib.suppress(OSError, AttributeError):
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    handle.write(line)
                    handle.flush()
                finally:
                    if fcntl is not None:
                        with contextlib.suppress(OSError, AttributeError):
                            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            return event
        except Exception as exc:  # noqa: BLE001
            return exc

    def list_events(self, *, since: str | None = None) -> list[MergeEvent] | Exception:
        try:
            if not self._path.is_file():
                return []
            rows: list[MergeEvent] = []
            for line in self._path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                raw = json.loads(stripped)
                if isinstance(raw, dict):
                    event = MergeEvent.model_validate(raw)
                    if since and event.at <= since:
                        continue
                    rows.append(event)
            return rows
        except Exception as exc:  # noqa: BLE001
            return exc


__all__ = ["MergeEventStore"]
