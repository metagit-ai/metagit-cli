#!/usr/bin/env python
"""
Runtime models for managed repository search and resolve results.
"""

from pydantic import BaseModel, Field


class ManagedRepoStatus(BaseModel):
    """Resolved sync state for a managed workspace repository row."""

    resolved_path: str
    exists: bool
    is_git_repo: bool
    sync_enabled: bool
    status: str


class ManagedRepoMatch(BaseModel):
    """One search hit with scoring metadata."""

    project_name: str
    repo_name: str
    url: str | None = None
    configured_path: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    project_tags: dict[str, str] = Field(default_factory=dict)
    repo_tags: dict[str, str] = Field(default_factory=dict)
    status: ManagedRepoStatus
    match_reasons: list[str] = Field(default_factory=list)
    score: int


class ManagedRepoSearchResult(BaseModel):
    """Ordered search hits for a query."""

    query: str
    matches: list[ManagedRepoMatch] = Field(default_factory=list)


class ManagedRepoError(BaseModel):
    """Structured error from resolve_one."""

    kind: str
    message: str
    matches: list[ManagedRepoMatch] = Field(default_factory=list)


class ManagedRepoResolveResult(BaseModel):
    """Single-match resolution or an error."""

    match: ManagedRepoMatch | None = None
    error: ManagedRepoError | None = None
