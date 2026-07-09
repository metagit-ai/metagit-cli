#!/usr/bin/env python
"""Pydantic models for the Agent Coordination Layer (RFC-0007)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

BranchStatus = Literal["allocated", "released", "archived"]
LeaseStatus = Literal["active", "expired", "released"]
WorktreeStatus = Literal["active", "destroyed"]
ClaimStatus = Literal["active", "released"]

AclEventType = Literal[
    "AgentStarted",
    "LeaseGranted",
    "LeaseExpired",
    "BranchAllocated",
    "BranchReleased",
    "ConflictDetected",
    "WorktreeCreated",
    "WorktreeDestroyed",
    "ClaimGranted",
    "ClaimConflict",
    "TaskCompleted",
    "TaskBlocked",
]


class BranchAllocation(BaseModel):
    """Recorded ownership of an agent/* branch."""

    branch_id: str
    name: str
    repository: str
    agent_id: str
    task_id: str
    integration_branch: Optional[str] = None
    status: BranchStatus = "allocated"
    base_ref: Optional[str] = None
    created_at: str
    updated_at: str


class Lease(BaseModel):
    """Temporary ownership of a branch for one agent/task."""

    lease_id: str
    branch: str
    repository: str
    agent_id: str
    task_id: str
    created: str
    expires: str
    status: LeaseStatus = "active"
    branch_id: Optional[str] = None


class WorktreeRecord(BaseModel):
    """Isolated git worktree bound to one agent and lease."""

    worktree_id: str
    path: str
    repository: str
    branch: str
    agent_id: str
    task_id: str
    lease_id: str
    status: WorktreeStatus = "active"
    created_at: str
    updated_at: str


class FileClaim(BaseModel):
    """Advisory file-path reservation within a repository."""

    claim_id: str
    repository: str
    agent_id: str
    patterns: list[str] = Field(default_factory=list)
    status: ClaimStatus = "active"
    task_id: Optional[str] = None
    created_at: str
    updated_at: str


class RepoAgentPresence(BaseModel):
    """Advisory registry of agents active in a repository."""

    repository: str
    agent_ids: list[str] = Field(default_factory=list)
    updated_at: str


class AgentExecutionManifest(BaseModel):
    """Canonical execution contract for one agent run."""

    agent_id: str
    task_id: str
    branch: str
    worktree: str
    repositories: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    integration_branch: Optional[str] = None
    context_budget: Optional[int] = None
    completion_requirements: list[str] = Field(default_factory=list)
    lease_id: Optional[str] = None
    created_at: Optional[str] = None


class AclEvent(BaseModel):
    """Typed ACL lifecycle event."""

    event_id: str
    type: AclEventType
    at: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ClaimConflict(BaseModel):
    """Structured advisory conflict when file claims overlap."""

    owner: str
    files: list[str] = Field(default_factory=list)
    claim_id: Optional[str] = None


class BranchListResult(BaseModel):
    """List envelope for branch allocations."""

    ok: bool = True
    branches: list[BranchAllocation] = Field(default_factory=list)


class LeaseListResult(BaseModel):
    """List envelope for leases."""

    ok: bool = True
    leases: list[Lease] = Field(default_factory=list)
    presence: list[RepoAgentPresence] = Field(default_factory=list)


class WorktreeListResult(BaseModel):
    """List envelope for worktrees."""

    ok: bool = True
    worktrees: list[WorktreeRecord] = Field(default_factory=list)


class ClaimListResult(BaseModel):
    """List envelope for file claims."""

    ok: bool = True
    claims: list[FileClaim] = Field(default_factory=list)


class ClaimCheckResult(BaseModel):
    """Result of an advisory claim overlap check."""

    ok: bool = True
    conflicts: list[ClaimConflict] = Field(default_factory=list)


class WorktreeStatusResult(BaseModel):
    """Git status summary for one or more worktrees."""

    ok: bool = True
    worktrees: list[dict[str, Any]] = Field(default_factory=list)


__all__ = [
    "AclEvent",
    "AclEventType",
    "AgentExecutionManifest",
    "BranchAllocation",
    "BranchListResult",
    "BranchStatus",
    "ClaimCheckResult",
    "ClaimConflict",
    "ClaimListResult",
    "ClaimStatus",
    "FileClaim",
    "Lease",
    "LeaseListResult",
    "LeaseStatus",
    "RepoAgentPresence",
    "WorktreeListResult",
    "WorktreeRecord",
    "WorktreeStatus",
    "WorktreeStatusResult",
]
