#!/usr/bin/env python
"""
Manual workspace graph relationships for cross-repo knowledge graphs.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

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
    component: Optional[str] = Field(
        None,
        description="Optional catalogued component name within the repo",
    )
    identity: Optional[str] = Field(
        None,
        description="Canonical repository identity (github://org/repo) when the endpoint is not a local checkout",
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
        description=("Relationship type (depends_on, documents, consumes, owns, related, …)"),
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
    status: Literal["active", "deprecated", "proposed"] = Field(
        default="active",
        description="Lifecycle state of this relationship",
    )
    provenance: Literal["manual", "promoted", "imported", "inferred", "github"] = Field(
        default="manual",
        description=(
            "Origin of this relationship (hand-authored, promoted from a suggestion, "
            "imported, inferred from observations, or GitHub-derived)"
        ),
    )

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: object) -> str:
        if value is None:
            return "depends_on"
        return str(value).strip().lower()


def graph_relationships_payload(
    relationships: list[GraphRelationship],
    *,
    include_defaults: bool = False,
) -> list[dict[str, Any]]:
    """Serialize relationships for YAML output using the ``from`` alias.

    ``status`` and ``provenance`` are always emitted so an edge's lifecycle stays
    explicit on disk even when it matches the model default.
    """
    payload: list[dict[str, Any]] = []
    for relationship in relationships:
        item = relationship.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
            exclude_defaults=not include_defaults,
        )
        item["status"] = relationship.status
        item["provenance"] = relationship.provenance
        payload.append(item)
    return payload


class GraphNode(BaseModel):
    """Curated Git-managed knowledge about a repository node, including external ones."""

    model_config = ConfigDict(extra="forbid")

    identity: Optional[str] = Field(
        None,
        description="Canonical identity such as github://org/repo",
    )
    name: Optional[str] = Field(None, description="Repository name")
    provider: Optional[str] = Field(None, description="Source provider (github, gitlab, …)")
    organization: Optional[str] = Field(None, description="Provider organization or namespace")
    classification: dict[str, str] = Field(
        default_factory=dict,
        description="Durable classification (domain, lifecycle, …)",
    )
    tags: dict[str, str] = Field(default_factory=dict, description="Curated tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible curated payload")


class WorkspaceGraph(BaseModel):
    """Top-level manual graph data on a .metagit.yml manifest."""

    model_config = ConfigDict(extra="forbid")

    relationships: list[GraphRelationship] = Field(
        default_factory=list,
        description="Manually entered cross-repo or cross-project edges",
    )
    nodes: list[GraphNode] = Field(
        default_factory=list,
        description="Optional curated repository nodes that may not be locally materialized",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Graph-level metadata for export pipelines",
    )
