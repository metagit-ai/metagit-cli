#!/usr/bin/env python
"""
Models for provider-based recursive repository discovery and sync planning.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from metagit.core.project.models import ProjectPath


class SourceProvider(str, Enum):
    """Supported source providers for recursive discovery."""

    GITHUB = "github"
    GITLAB = "gitlab"


class SourceSyncMode(str, Enum):
    """Supported sync planning modes."""

    DISCOVER = "discover"
    ADDITIVE = "additive"
    RECONCILE = "reconcile"


class SourceSpec(BaseModel):
    """Input specification for source-backed repository discovery."""

    provider: SourceProvider = Field(..., description="Source provider")
    org: Optional[str] = Field(None, description="GitHub organization")
    user: Optional[str] = Field(None, description="GitHub user")
    group: Optional[str] = Field(None, description="GitLab group path")
    recursive: bool = Field(
        True, description="Whether to recurse into nested scopes when supported"
    )
    include_archived: bool = Field(
        False, description="Include archived repositories in discovery"
    )
    include_forks: bool = Field(False, description="Include forked repositories")
    path_prefix: Optional[str] = Field(
        None, description="Optional namespace/repo prefix filter"
    )

    @model_validator(mode="after")
    def validate_scope(self) -> "SourceSpec":
        if self.provider == SourceProvider.GITHUB:
            selectors = [self.org, self.user]
            if sum(1 for value in selectors if value) != 1:
                raise ValueError(
                    "GitHub source requires exactly one of --org or --user"
                )
            if self.group:
                raise ValueError("GitHub source cannot use --group")
        if self.provider == SourceProvider.GITLAB:
            if not self.group:
                raise ValueError("GitLab source requires --group")
            if self.org or self.user:
                raise ValueError("GitLab source cannot use --org or --user")
        return self

    @property
    def namespace_key(self) -> str:
        """Canonical source namespace used for provenance and reconcile boundaries."""
        if self.provider == SourceProvider.GITHUB:
            return self.org if self.org else self.user or ""
        return self.group or ""


class DiscoveredRepo(BaseModel):
    """Normalized repository shape discovered from provider APIs."""

    provider: SourceProvider
    namespace: str
    full_name: str
    name: str
    clone_url: str
    default_branch: Optional[str] = None
    description: Optional[str] = None
    repo_id: Optional[str] = None
    archived: bool = False
    fork: bool = False
    private: Optional[bool] = None


class SourceSyncPlan(BaseModel):
    """Computed workspace changes for source-backed sync modes."""

    discovered_count: int = 0
    unchanged: int = 0
    to_add: List[ProjectPath] = Field(default_factory=list)
    to_update: List[ProjectPath] = Field(default_factory=list)
    to_remove: List[ProjectPath] = Field(default_factory=list)
