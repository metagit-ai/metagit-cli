#!/usr/bin/env python
"""
Pydantic models for workspace project context and snapshot persistence.
"""

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from metagit.core.workspace.agent_instructions import AgentInstructionLayer

_ENV_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+", re.IGNORECASE),
    re.compile(r"-----BEGIN"),
)
_MAX_AGENT_NOTES = 4096
_MAX_RECENT_REPOS = 10


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO8601 format."""
    return datetime.now(timezone.utc).isoformat()


def validate_env_key(key: str) -> str:
    """Validate environment variable key naming."""
    if not _ENV_KEY_PATTERN.match(key):
        raise ValueError(f"Invalid environment key: {key}")
    return key


def validate_env_value(value: str) -> str:
    """Reject values that look like secrets."""
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            raise ValueError("Environment value appears to contain secret material.")
    return value


class WorkspaceSessionMeta(BaseModel):
    """Workspace-level session metadata."""

    active_project: Optional[str] = None
    last_switch_at: Optional[str] = None
    last_snapshot_id: Optional[str] = None
    last_session_at: Optional[str] = None


class ProjectSession(BaseModel):
    """Per-project persisted session state."""

    project_name: str
    updated_at: str = Field(default_factory=utc_now_iso)
    recent_repos: list[str] = Field(default_factory=list)
    primary_repo_path: Optional[str] = None
    agent_notes: Optional[str] = None
    env_overrides: dict[str, str] = Field(default_factory=dict)
    last_snapshot_id: Optional[str] = None

    @field_validator("agent_notes")
    @classmethod
    def validate_agent_notes(cls, value: Optional[str]) -> Optional[str]:
        """Bound agent notes length."""
        if value is not None and len(value) > _MAX_AGENT_NOTES:
            raise ValueError(f"agent_notes exceeds {_MAX_AGENT_NOTES} characters.")
        return value

    @field_validator("recent_repos")
    @classmethod
    def validate_recent_repos(cls, value: list[str]) -> list[str]:
        """Cap recent repo list length."""
        return value[:_MAX_RECENT_REPOS]

    @field_validator("env_overrides")
    @classmethod
    def validate_env_overrides(cls, value: dict[str, str]) -> dict[str, str]:
        """Validate non-secret environment overrides."""
        validated: dict[str, str] = {}
        for key, env_value in value.items():
            validated[validate_env_key(key)] = validate_env_value(env_value)
        return validated


class ProjectRepoContext(BaseModel):
    """Repository row included in a project context bundle."""

    repo_name: str
    repo_path: str
    configured_path: Optional[str] = None
    exists: bool = False
    branch: Optional[str] = None
    dirty: Optional[bool] = None
    tags: dict[str, str] = Field(default_factory=dict)
    agent_instructions: Optional[str] = None
    inspect_error: Optional[str] = None


class ProjectContextEnv(BaseModel):
    """Environment exports and hints for agents."""

    export: dict[str, str] = Field(default_factory=dict)
    hints: list[str] = Field(default_factory=list)


class ProjectContextSession(BaseModel):
    """Session slice returned with a context bundle."""

    restored: bool = False
    recent_repos: list[str] = Field(default_factory=list)
    primary_repo_path: Optional[str] = None
    agent_notes: Optional[str] = None


class ProjectContextBundle(BaseModel):
    """Result of switching or showing project context."""

    ok: bool = True
    error: Optional[str] = None
    project_name: str = ""
    workspace_root: str = ""
    project_description: Optional[str] = None
    agent_instructions: Optional[str] = None
    instruction_layers: list[AgentInstructionLayer] = Field(default_factory=list)
    effective_agent_instructions: str = ""
    focus_repo_name: Optional[str] = None
    repos: list[ProjectRepoContext] = Field(default_factory=list)
    env: ProjectContextEnv = Field(default_factory=ProjectContextEnv)
    session: ProjectContextSession = Field(default_factory=ProjectContextSession)
    suggested_cwd: Optional[str] = None
    inspect_truncated: bool = False


class SnapshotRepoState(BaseModel):
    """Git state for one repository in a snapshot."""

    project_name: str
    repo_name: str
    repo_path: str
    branch: Optional[str] = None
    dirty: bool = False
    ahead: Optional[int] = None
    behind: Optional[int] = None
    uncommitted_count: Optional[int] = None
    inspect_error: Optional[str] = None


class WorkspaceSnapshot(BaseModel):
    """Immutable workspace state manifest."""

    snapshot_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    active_project: Optional[str] = None
    label: Optional[str] = None
    repos: list[SnapshotRepoState] = Field(default_factory=list)
    env_key_names: list[str] = Field(default_factory=list)
    session_ref: Optional[str] = None


class WorkspaceSnapshotRestoreResult(BaseModel):
    """Result of restoring a workspace snapshot."""

    ok: bool = True
    error: Optional[str] = None
    snapshot_id: str = ""
    context: Optional[ProjectContextBundle] = None
    notes: list[str] = Field(default_factory=list)
