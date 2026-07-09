#!/usr/bin/env python
"""Tests for RFC-0011 merge orchestrator JSON store."""

from __future__ import annotations

import json

from metagit.core.merge.models import MergeQueue, MergeRequest
from metagit.core.merge.paths import events_file, merge_file, merges_root, queue_file
from metagit.core.merge.store import MergeStore


def _request(merge_id: str, *, status: str = "queued") -> MergeRequest:
    return MergeRequest(
        merge_id=merge_id,
        repository="project/repo",
        source_branch=f"agent/{merge_id}",
        target_branch="main",
        status=status,  # type: ignore[arg-type]
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )


def test_merge_paths_resolve_under_metagit_session_root(tmp_path) -> None:
    assert merges_root(str(tmp_path)) == tmp_path / ".metagit" / "merges"
    assert queue_file(str(tmp_path)) == tmp_path / ".metagit" / "merges" / "queue.json"
    assert merge_file(str(tmp_path), "merge-001") == tmp_path / ".metagit" / "merges" / "merge-001.json"
    assert events_file(str(tmp_path)) == tmp_path / ".metagit" / "events" / "merge.jsonl"


def test_store_returns_missing_merge_as_exception_and_empty_queue(tmp_path) -> None:
    store = MergeStore(str(tmp_path))

    missing = store.load("merge-001")
    queue = store.load_queue()

    assert isinstance(missing, FileNotFoundError)
    assert queue == MergeQueue()


def test_store_saves_and_loads_merge_document(tmp_path) -> None:
    store = MergeStore(str(tmp_path))
    request = _request("merge-001", status="running")

    saved = store.save(request)
    loaded = store.load("merge-001")

    assert saved is None
    assert loaded == request

    raw = json.loads(merge_file(str(tmp_path), "merge-001").read_text(encoding="utf-8"))
    assert raw["merge_id"] == "merge-001"
    assert raw["status"] == "running"


def test_store_saves_queue_index_sorted_by_merge_id(tmp_path) -> None:
    store = MergeStore(str(tmp_path))

    first = store.save(_request("merge-b", status="queued"))
    second = store.save(_request("merge-a", status="conflict"))
    queue = store.load_queue()

    assert first is None
    assert second is None
    assert not isinstance(queue, Exception)
    assert [entry.merge_id for entry in queue.merges] == ["merge-a", "merge-b"]
    assert queue.merges[0].status == "conflict"
    assert queue.merges[1].status == "queued"


def test_store_saves_explicit_queue(tmp_path) -> None:
    store = MergeStore(str(tmp_path))
    queue = MergeQueue()

    saved = store.save_queue(queue)

    assert saved is None
    assert store.load_queue() == queue
