#!/usr/bin/env python
"""
Pydantic models for context packs (T0 workspace map and T1 repo cards).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


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


class ContextPackResult(BaseModel):
    """Unified context pack envelope for tier 0/1 MCP and CLI payloads."""

    ok: bool = True
    tier: Literal[0, 1]
    workspace_name: str
    map: Optional[WorkspaceMapResult] = Field(
        default=None,
        description="Tier 0 map when included.",
    )
    cards: Optional[list[RepoCardResult]] = Field(
        default=None,
        description="Tier 1 repo cards when included.",
    )
    token_estimate: Optional[int] = None
