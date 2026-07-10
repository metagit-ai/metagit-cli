#!/usr/bin/env python
"""Unit tests for scheduler models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from metagit.core.scheduler.models import ScheduleDecision, SchedulePolicy
from metagit.core.taskgraph.models import TaskNode


def test_schedule_policy_defaults() -> None:
    policy = SchedulePolicy()
    assert policy.weights.priority == 1.0
    assert policy.weights.affinity == 0.5
    assert policy.weights.cost == 0.25
    assert policy.weights.fairness == 0.0
    assert policy.merge_queue_threshold == 3
    assert policy.skip_on_merge_pressure is False


def test_schedule_policy_rejects_invalid_threshold() -> None:
    with pytest.raises(ValidationError):
        SchedulePolicy(merge_queue_threshold=0)


def test_schedule_decision_validates_ids() -> None:
    with pytest.raises(ValidationError):
        ScheduleDecision(
            decision_id="bad id",
            at="2026-07-09T00:00:00Z",
            graph_id="g1",
            node_id="n1",
            score=1.0,
        )


def test_task_node_priority_defaults_to_zero() -> None:
    node = TaskNode(
        node_id="n1",
        graph_id="g1",
        title="Root",
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )
    assert node.priority == 0
    assert node.estimated_tokens is None
