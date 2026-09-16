#!/usr/bin/env python
"""Repository node models for local and external graph endpoints."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RepoPresence = Literal["known", "indexed", "materialized"]
RepoLifecycle = Literal["active", "archived", "deleted", "unknown"]
RepoProvenance = Literal["local", "github", "imported", "inferred", "manual"]


class RepositoryNode(BaseModel):
    """A resolvable repository regardless of local checkout state."""

    model_config = ConfigDict(extra="forbid")

    identity: str = Field(..., description="Canonical identity such as github://org/repo")
    name: str
    provider: str = "github"
    organization: Optional[str] = None
    presence: RepoPresence = "known"
    lifecycle: RepoLifecycle = "active"
    provenance: list[RepoProvenance] = Field(default_factory=list)
    url: Optional[str] = None
    clone_url: Optional[str] = None
    project_name: Optional[str] = None
    local_path: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    topics: list[str] = Field(default_factory=list)
    detected: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def graph_node_id(self) -> str:
        """Stable graph node id; GitHub identities win, else repo:project/name."""
        if self.identity.startswith("github://"):
            return self.identity
        if self.project_name:
            return f"repo:{self.project_name}/{self.name}"
        return f"repo:{self.name}"

    @property
    def is_materialized(self) -> bool:
        return self.presence == "materialized"
