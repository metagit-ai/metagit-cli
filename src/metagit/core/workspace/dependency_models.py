#!/usr/bin/env python
"""
Pydantic models for cross-project dependency graph results.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

DependencyEdgeType = Literal[
    "declared",
    "import",
    "shared_config",
    "url_match",
    "ref",
    "manual",
]


class DependencyNode(BaseModel):
    """Node in a workspace dependency graph."""

    id: str
    kind: Literal["project", "repo"]
    label: str
    project_name: Optional[str] = None
    repo_path: Optional[str] = None
    gitnexus_indexed: Optional[bool] = None
    gitnexus_status: Optional[str] = None


class DependencyEdge(BaseModel):
    """Directed dependency edge with evidence."""

    from_id: str
    to_id: str
    type: DependencyEdgeType
    evidence: list[str] = Field(default_factory=list)


class ImpactSummary(BaseModel):
    """High-level impact assessment for dependency exploration."""

    risk: Literal["low", "medium", "high"] = "low"
    affected_projects: list[str] = Field(default_factory=list)
    affected_repos: list[str] = Field(default_factory=list)
    edge_count: int = 0
    notes: list[str] = Field(default_factory=list)


class CrossProjectDependencyResult(BaseModel):
    """Result of cross-project dependency mapping."""

    ok: bool = True
    error: Optional[str] = None
    source_project: str = ""
    dependency_types: list[str] = Field(default_factory=list)
    depth: int = 1
    graph_status: dict[str, str] = Field(default_factory=dict)
    nodes: list[DependencyNode] = Field(default_factory=list)
    edges: list[DependencyEdge] = Field(default_factory=list)
    impact_summary: ImpactSummary = Field(default_factory=ImpactSummary)
