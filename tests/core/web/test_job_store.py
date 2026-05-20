#!/usr/bin/env python
"""Unit tests for SyncJobStore."""

from metagit.core.web.job_store import SyncJobStore


def test_job_lifecycle_and_events() -> None:
    store = SyncJobStore()
    job_id = store.create_job()
    store.mark_running(job_id)
    store.append_event(job_id, {"type": "progress", "done": 1, "total": 2})
    store.complete(job_id, summary={"ok": 1}, results=[{"repo": "a"}])
    status = store.get(job_id)
    assert status is not None
    assert status.state == "completed"
    events = store.drain_events(job_id)
    assert len(events) == 1
