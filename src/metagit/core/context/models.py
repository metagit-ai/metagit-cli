#!/usr/bin/env python
"""
Pydantic models for context packs (T0 workspace map and T1 repo cards).
"""

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

_OBJECTIVE_ID_PATTERN = re.compile(r"^[\w.-]+$")


class WorkspaceMapEntry(BaseModel):
    """Repo row embedded in the T0 workspace map."""

    project_name: str
    repo_name: str
    repo_path: str
    status: str
    exists: bool
    tags: Optional[list[str]] = None


class WorkspaceMapProject(BaseModel):
    """Project summary row embedded in the T0 workspace map."""

    name: str
    repo_count: int
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    protected: bool = False


class WorkspaceMapResult(BaseModel):
    """Structured T0 workspace map payload."""

    tier: Literal[0] = 0
    workspace_name: str
    workspace_root: str
    config_path: str
    project_count: int
    repo_count: int
    projects: list[WorkspaceMapProject]
    repos: list[WorkspaceMapEntry]
    active_project: Optional[str] = None


class RepoCardResult(BaseModel):
    """Structured T1 repo card payload."""

    tier: Literal[1] = 1
    project_name: str
    repo_name: str
    repo_path: str
    status: str
    exists: bool
    is_git_repo: bool
    branch: str
    dirty: bool
    ahead: int
    behind: int
    head_commit_age_days: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    url: Optional[str] = None
    description: Optional[str] = None
    agent_instructions_excerpt: Optional[str] = None
    stack_hints: list[str] = Field(default_factory=list)
    health_flags: list[str] = Field(default_factory=list)


class SessionDigestRepoChange(BaseModel):
    """Git activity for one repo since the last session boundary."""

    project_name: str
    repo_name: str
    repo_path: str
    commit_count: int = 0
    recent_subjects: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class SessionDigestResult(BaseModel):
    """T2 digest: workspace changes since last session."""

    tier: Literal[2] = 2
    since: Optional[str] = None
    first_session: bool = False
    manifest_changed: bool = False
    active_objective_id: Optional[str] = None
    repo_changes: list[SessionDigestRepoChange] = Field(default_factory=list)


ObjectiveStatus = Literal["pending", "in_progress", "done", "cancelled"]


class Objective(BaseModel):
    """Shared human/agent workspace objective."""

    id: str
    status: ObjectiveStatus = "pending"
    title: str
    repos: list[str] = Field(default_factory=list)
    acceptance: Optional[str] = None
    human_notes: Optional[str] = None
    agent_notes: Optional[str] = None
    mr_url: Optional[str] = Field(
        default=None,
        description="Merge request or pull request URL produced by this objective",
    )
    approval_id: Optional[str] = Field(
        default=None,
        description="Approval queue id when work is gated on human review",
    )
    created_at: str
    updated_at: str

    @field_validator("id")
    @classmethod
    def validate_id_slug(cls, value: str) -> str:
        if not _OBJECTIVE_ID_PATTERN.match(value):
            raise ValueError("objective id must match slug pattern [alphanumeric, underscore, dot, hyphen]")
        return value

    @field_validator("title")
    @classmethod
    def validate_title_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title is required")
        return stripped

    @field_validator("repos")
    @classmethod
    def validate_repos_strings(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str):
                raise ValueError("repos entries must be strings")
        return value


class ObjectiveListResult(BaseModel):
    """List of workspace objectives."""

    ok: bool = True
    objectives: list[Objective] = Field(default_factory=list)


ApprovalStatus = Literal["pending", "approved", "denied"]
HandoffStatus = Literal["open", "claimed", "completed", "cancelled"]


class ApprovalRequest(BaseModel):
    """Pending or resolved approval for a mutating workspace operation."""

    id: str
    action: str
    status: ApprovalStatus = "pending"
    requested_by: str = "agent"
    idempotency_key: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    resolved_at: Optional[str] = None
    resolver_note: Optional[str] = None


class ApprovalListResult(BaseModel):
    """Approval queue listing."""

    ok: bool = True
    requests: list[ApprovalRequest] = Field(default_factory=list)


class ContextPackResult(BaseModel):
    """Unified context pack envelope for tier 0/1/2 MCP and CLI payloads."""

    ok: bool = True
    tier: Literal[0, 1, 2]
    workspace_name: str
    map: Optional[WorkspaceMapResult] = Field(
        default=None,
        description="Tier 0 map when included.",
    )
    cards: Optional[list[RepoCardResult]] = Field(
        default=None,
        description="Tier 1 repo cards when included.",
    )
    digest: Optional[SessionDigestResult] = Field(
        default=None,
        description="Tier 2 session digest when included.",
    )
    dropped_sections: list[str] = Field(default_factory=list)
    max_tokens: Optional[int] = None
    token_estimate: Optional[int] = None


class SessionBeginResult(BaseModel):
    """Deterministic session-start envelope for agents and orchestration."""

    ok: bool = True
    schema_version: str = "1.0"
    workspace_name: str
    active_project: Optional[str] = None
    session: dict[str, Any] = Field(default_factory=dict)
    objectives: list[Objective] = Field(default_factory=list)
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    handoffs: list[dict[str, Any]] = Field(default_factory=list)
    pack: ContextPackResult
    prompt: str = ""
    warnings: list[str] = Field(default_factory=list)


class HandoffEvent(BaseModel):
    """Audit trail entry for handoff state transitions."""

    at: str
    by: str
    action: str
    note: Optional[str] = None


class HandoffItem(BaseModel):
    """Coordinated work handoff object."""

    id: str
    title: str
    status: HandoffStatus = "open"
    created_by: str = "agent"
    claimed_by: Optional[str] = None
    claim_expires_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when an active claim auto-releases",
    )
    last_heartbeat_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp of the latest claim heartbeat",
    )
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    events: list[HandoffEvent] = Field(default_factory=list)


class HandoffListResult(BaseModel):
    """List of handoff items."""

    ok: bool = True
    handoffs: list[HandoffItem] = Field(default_factory=list)


class WorkspaceEvent(BaseModel):
    """Timeline row for incremental event polling."""

    timestamp: str
    source: str
    kind: str
    id: str
    data: dict[str, Any] = Field(default_factory=dict)


class WorkspaceEventsResult(BaseModel):
    """Incremental events feed with cursor support."""

    ok: bool = True
    schema_version: str = "1.0"
    since: Optional[str] = None
    next_cursor: Optional[str] = None
    events: list[WorkspaceEvent] = Field(default_factory=list)
