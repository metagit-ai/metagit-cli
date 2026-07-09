#!/usr/bin/env python
"""Tests for RFC-0011 merge orchestrator models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from metagit.core.merge.models import (
    MergeConflict,
    MergeQueue,
    MergeQueueEntry,
    MergeRequest,
    MergeValidation,
    MergeValidationCommand,
)


def test_merge_request_accepts_minimum_required_fields() -> None:
    request = MergeRequest(
        merge_id="merge-001",
        repository="project/repo",
        source_branch="agent/task-1",
        target_branch="main",
        status="queued",
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )

    assert request.merge_id == "merge-001"
    assert request.repository == "project/repo"
    assert request.status == "queued"
    assert request.node_id is None
    assert request.acl_commands == []


def test_merge_request_validates_slug_repository_and_status() -> None:
    with pytest.raises(ValidationError):
        MergeRequest(
            merge_id="bad id",
            repository="repo-only",
            source_branch="agent/task-1",
            target_branch="main",
            status="waiting",
            created_at="2026-07-09T00:00:00Z",
            updated_at="2026-07-09T00:00:00Z",
        )


def test_merge_request_cleans_nested_conflict_and_validation() -> None:
    request = MergeRequest(
        merge_id="merge-002",
        repository="project/repo",
        source_branch="agent/task-2",
        target_branch="main",
        status="validation_failed",
        conflict=MergeConflict(
            files=[" src/app.py ", "", "tests/test_app.py"],
            message="  resolve manually  ",
            dispatch_hint="  rerun after fix  ",
        ),
        validation=MergeValidation(
            ok=False,
            commands=[
                MergeValidationCommand(
                    cmd=" task test ",
                    exit_code=1,
                    stdout="out",
                    stderr="err",
                ),
            ],
        ),
        acl_commands=[" metagit claim declare "],
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )

    assert request.conflict is not None
    assert request.conflict.files == ["src/app.py", "tests/test_app.py"]
    assert request.conflict.message == "resolve manually"
    assert request.conflict.dispatch_hint == "rerun after fix"
    assert request.validation is not None
    assert request.validation.commands[0].cmd == "task test"
    assert request.acl_commands == ["metagit claim declare"]


def test_merge_queue_entry_validates_merge_id() -> None:
    queue = MergeQueue(
        merges=[
            MergeQueueEntry(
                merge_id="merge-001",
                repository="project/repo",
                status="running",
                updated_at="2026-07-09T00:00:00Z",
            ),
        ],
    )

    assert queue.merges[0].merge_id == "merge-001"

    with pytest.raises(ValidationError):
        MergeQueueEntry(
            merge_id="bad id",
            repository="project/repo",
            status="queued",
            updated_at="2026-07-09T00:00:00Z",
        )
