#!/usr/bin/env python
"""Pydantic models for the Task Graph & Intent Engine (RFC-0008)."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

_ID_PATTERN = re.compile(r"^[\w.-]+$")

TaskNodeStatus = Literal["pending", "ready", "blocked", "running", "completed", "cancelled"]
TaskGraphStatus = Literal["active", "completed", "cancelled"]

TaskGraphEventType = Literal[
    "TaskGraphCreated",
    "TaskNodeCreated",
    "TaskReady",
    "TaskBlocked",
    "TaskCompleted",
    "TaskCancelled",
    "TaskStarted",
]


def _validate_id(value: str, *, label: str) -> str:
    stripped = value.strip()
    if not stripped or not _ID_PATTERN.match(stripped):
        raise ValueError(f"{label} must match slug pattern [alphanumeric, underscore, dot, hyphen]")
    return stripped


class TaskAclBinding(BaseModel):
    """Optional ACL resource ids and suggested CLI command strings (hints only)."""

    branch: Optional[str] = None
    lease_id: Optional[str] = None
    worktree_id: Optional[str] = None
    claim_ids: list[str] = Field(default_factory=list)
    acl_commands: list[str] = Field(default_factory=list)


class TaskIntent(BaseModel):
    """Structured intent attached to a graph or node."""

    intent_id: str
    title: str
    goal: str
    acceptance: list[str] = Field(default_factory=list)
    project: Optional[str] = None
    repos: list[str] = Field(default_factory=list)
    objective_id: Optional[str] = None
    handoff_id: Optional[str] = None
    created_at: str
    updated_at: str

    @field_validator("intent_id")
    @classmethod
    def validate_intent_id(cls, value: str) -> str:
        return _validate_id(value, label="intent_id")

    @field_validator("title", "goal")
    @classmethod
    def validate_nonempty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title and goal must be non-empty")
        return stripped


class TaskNode(BaseModel):
    """One executable node in a task DAG."""

    node_id: str
    graph_id: str
    title: str
    depends_on: list[str] = Field(default_factory=list)
    status: TaskNodeStatus = "pending"
    intent_id: Optional[str] = None
    blocker_reason: Optional[str] = None
    project: Optional[str] = None
    repository: Optional[str] = None
    agent_id: Optional[str] = None
    acl: Optional[TaskAclBinding] = None
    context_budget: Optional[int] = None
    compiled_context_path: Optional[str] = None
    created_at: str
    updated_at: str

    @field_validator("node_id", "graph_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title is required")
        return stripped


class TaskGraph(BaseModel):
    """A DAG of task nodes under one graph id."""

    graph_id: str
    title: str
    root_intent_id: Optional[str] = None
    objective_id: Optional[str] = None
    handoff_id: Optional[str] = None
    intent: Optional[TaskIntent] = None
    nodes: list[TaskNode] = Field(default_factory=list)
    status: TaskGraphStatus = "active"
    created_at: str
    updated_at: str

    @field_validator("graph_id")
    @classmethod
    def validate_graph_id(cls, value: str) -> str:
        return _validate_id(value, label="graph_id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title is required")
        return stripped

    def node_map(self) -> dict[str, TaskNode]:
        return {node.node_id: node for node in self.nodes}


class TaskGraphEvent(BaseModel):
    """Typed task-graph lifecycle event."""

    event_id: str
    type: TaskGraphEventType
    at: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskGraphIndexEntry(BaseModel):
    """Lightweight listing row for ``index.json``."""

    graph_id: str
    title: str
    status: TaskGraphStatus
    objective_id: Optional[str] = None
    updated_at: str


class TaskGraphIndex(BaseModel):
    """Optional index of graphs under ``.metagit/tasks/``."""

    graphs: list[TaskGraphIndexEntry] = Field(default_factory=list)


__all__ = [
    "TaskAclBinding",
    "TaskGraph",
    "TaskGraphEvent",
    "TaskGraphEventType",
    "TaskGraphIndex",
    "TaskGraphIndexEntry",
    "TaskGraphStatus",
    "TaskIntent",
    "TaskNode",
    "TaskNodeStatus",
]
