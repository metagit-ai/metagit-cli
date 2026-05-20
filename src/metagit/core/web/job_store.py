#!/usr/bin/env python
"""In-memory sync job tracking for web UI SSE flows."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from metagit.core.web.models import SyncJobStatus


class SyncJobStore:
    """Thread-safe in-memory sync job tracking."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, SyncJobStatus] = {}
        self._pending_events: dict[str, list[dict[str, Any]]] = {}

    def create_job(self) -> str:
        """Create a pending job and return its id (uuid4 hex)."""
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = SyncJobStatus(job_id=job_id, state="pending")
            self._pending_events[job_id] = []
        return job_id

    def mark_running(self, job_id: str) -> None:
        """Mark an existing job as running."""
        with self._lock:
            status = self._jobs.get(job_id)
            if status is None:
                return
            self._jobs[job_id] = status.model_copy(update={"state": "running"})

    def append_event(self, job_id: str, event: dict[str, Any]) -> None:
        """Append a server-sent event payload for a job."""
        with self._lock:
            if job_id not in self._jobs:
                return
            self._pending_events.setdefault(job_id, []).append(dict(event))

    def complete(
        self,
        job_id: str,
        *,
        summary: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> None:
        """Mark a job completed with summary and per-repo results."""
        with self._lock:
            status = self._jobs.get(job_id)
            if status is None:
                return
            self._jobs[job_id] = status.model_copy(
                update={
                    "state": "completed",
                    "summary": dict(summary),
                    "results": list(results),
                    "error": None,
                }
            )

    def fail(self, job_id: str, error: str) -> None:
        """Mark a job as failed with an error message."""
        with self._lock:
            status = self._jobs.get(job_id)
            if status is None:
                return
            self._jobs[job_id] = status.model_copy(
                update={"state": "failed", "error": error}
            )

    def get(self, job_id: str) -> SyncJobStatus | None:
        """Return a snapshot of job status, or None if unknown."""
        with self._lock:
            status = self._jobs.get(job_id)
            return None if status is None else status.model_copy(deep=True)

    def drain_events(self, job_id: str) -> list[dict[str, Any]]:
        """Return pending SSE-style events for a job and clear the buffer."""
        with self._lock:
            pending = self._pending_events.pop(job_id, [])
            return [dict(e) for e in pending]
