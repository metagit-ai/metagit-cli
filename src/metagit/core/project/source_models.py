#!/usr/bin/env python
"""
Models for provider-based recursive repository discovery and sync planning.
"""

from enum import Enum
import re
from typing import Any, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

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
    include_patterns: List[str] = Field(
        default_factory=list,
        description="fnmatch allowlist on provider full_name; empty means no allowlist",
    )
    ignore_patterns: List[str] = Field(
        default_factory=list,
        description="fnmatch denylist on provider full_name",
    )
    ignore_languages: List[str] = Field(
        default_factory=list,
        description="Drop repos whose language matches (case-insensitive)",
    )
    visibility: Literal["any", "public", "private", "internal"] = Field(
        "any",
        description="Filter by repository visibility when provider exposes it",
    )
    name_strategy: Literal["short", "namespaced"] = Field(
        "namespaced",
        description="How to derive manifest repo names from discovered repos",
    )
    ensure: bool = Field(
        False,
        description="Skip metadata updates for repos already matched by URL or repo id",
    )
    refresh_metadata: bool = Field(
        False,
        description="With ensure, still update description/tags when provider changed",
    )
    enrich_topics: bool = Field(
        True,
        description="Merge provider topics into repo tags when authenticated",
    )
    source_id: Optional[str] = Field(
        None,
        description="Declarative source id from workspace.projects[].sources[]",
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


class ProjectSource(BaseModel):
    """Declarative provider import scope stored on ``workspace.projects[]``."""

    id: str = Field(..., description="Stable slug unique within the project")
    provider: SourceProvider = Field(..., description="Source provider")
    org: Optional[str] = Field(None, description="GitHub organization")
    user: Optional[str] = Field(None, description="GitHub user")
    group: Optional[str] = Field(None, description="GitLab group path")
    mode: SourceSyncMode = Field(
        SourceSyncMode.ADDITIVE,
        description="additive or reconcile (discover is CLI-only)",
    )
    recursive: bool = Field(
        True, description="Recurse into nested scopes when supported"
    )
    ensure: bool = Field(True, description="Skip metadata updates for existing URLs")
    refresh_metadata: bool = Field(
        False,
        description="With ensure, still refresh description/tags",
    )
    enrich_topics: bool = Field(
        True, description="Merge provider topics into repo tags"
    )
    include_archived: bool = Field(False, description="Include archived repositories")
    include_forks: bool = Field(False, description="Include forked repositories")
    path_prefix: Optional[str] = Field(
        None, description="Optional namespace/repo prefix"
    )
    include_patterns: List[str] = Field(default_factory=list)
    ignore_patterns: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("ignore_patterns", "ignore"),
    )
    name_strategy: Literal["short", "namespaced"] = Field("namespaced")
    enabled: bool = Field(True, description="When false, skip during manifest sync")

    @field_validator("id")
    @classmethod
    def validate_id_slug(cls, value: str) -> str:
        trimmed = value.strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", trimmed):
            raise ValueError(
                "source id must be a lowercase slug (letters, numbers, hyphens)"
            )
        return trimmed

    @model_validator(mode="after")
    def validate_manifest_source(self) -> "ProjectSource":
        if self.mode == SourceSyncMode.DISCOVER:
            raise ValueError(
                "sources[].mode cannot be discover; use additive or reconcile"
            )
        _ = SourceSpec(
            provider=self.provider,
            org=self.org,
            user=self.user,
            group=self.group,
        )
        return self

    def to_source_spec(self) -> SourceSpec:
        """Convert manifest source entry to runtime discovery spec."""
        return SourceSpec(
            provider=self.provider,
            org=self.org,
            user=self.user,
            group=self.group,
            recursive=self.recursive,
            include_archived=self.include_archived,
            include_forks=self.include_forks,
            path_prefix=self.path_prefix,
            include_patterns=list(self.include_patterns),
            ignore_patterns=list(self.ignore_patterns),
            name_strategy=self.name_strategy,
            ensure=self.ensure,
            refresh_metadata=self.refresh_metadata,
            enrich_topics=self.enrich_topics,
            source_id=self.id,
        )


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
    language: Optional[str] = None
    topics: List[str] = Field(default_factory=list)


class SourceSyncPlan(BaseModel):
    """Computed workspace changes for source-backed sync modes."""

    discovered_count: int = 0
    unchanged: int = 0
    to_add: List[ProjectPath] = Field(default_factory=list)
    to_update: List[ProjectPath] = Field(default_factory=list)
    to_remove: List[ProjectPath] = Field(default_factory=list)
    filtered_count: int = 0


class SourceSyncError(BaseModel):
    """Structured error for source sync JSON responses."""

    kind: str
    message: str


class SourceSyncResult(BaseModel):
    """CLI/MCP JSON envelope for source sync operations."""

    ok: bool = True
    applied: bool = False
    spec: Optional[dict[str, Any]] = None
    plan: Optional[SourceSyncPlan] = None
    errors: List[SourceSyncError] = Field(default_factory=list)
    pending_approval_id: Optional[str] = None
