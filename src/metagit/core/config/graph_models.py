#!/usr/bin/env python
"""
Manual workspace graph relationships for cross-repo knowledge graphs.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class GraphEndpoint(BaseModel):
    """Endpoint for a manual cross-repo relationship."""

    model_config = ConfigDict(extra="forbid")

    project: Optional[str] = Field(
        None,
        description="Workspace project name",
    )
    repo: Optional[str] = Field(
        None,
        description="Repository name under the project",
    )
    path: Optional[str] = Field(
        None,
        description="Optional file or directory path within the repo",
    )


class GraphRelationship(BaseModel):
    """Manually declared edge between workspace projects or repos."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: Optional[str] = Field(
        None,
        description="Stable identifier for exports and graph merges",
    )
    from_endpoint: GraphEndpoint = Field(
        ...,
        validation_alias=AliasChoices("from", "from_endpoint"),
        serialization_alias="from",
        description="Relationship source",
    )
    to: GraphEndpoint = Field(..., description="Relationship target")
    type: str = Field(
        default="depends_on",
        description=(
            "Relationship type (depends_on, documents, consumes, owns, related, …)"
        ),
    )
    label: Optional[str] = Field(None, description="Short label for graph UIs")
    description: Optional[str] = Field(
        None,
        description="Longer explanation for agents and exports",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Flat tags for filtering graph exports",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible payload for GitNexus or other graph ingestors",
    )

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: object) -> str:
        if value is None:
            return "depends_on"
        return str(value).strip().lower()


class WorkspaceGraph(BaseModel):
    """Top-level manual graph data on a .metagit.yml manifest."""

    model_config = ConfigDict(extra="forbid")

    relationships: list[GraphRelationship] = Field(
        default_factory=list,
        description="Manually entered cross-repo or cross-project edges",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Graph-level metadata for export pipelines",
    )
