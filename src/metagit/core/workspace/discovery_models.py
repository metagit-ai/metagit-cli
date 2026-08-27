#!/usr/bin/env python
"""
Pydantic models for workspace discovery / readiness (RFC-0020).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DiscoveryGateStatus(BaseModel):
    """Workspace gate evaluation for discovery summary."""

    state: str
    reason: Optional[str] = None


class DiscoveryMapStats(BaseModel):
    """Tier-0 style workspace map counts (lean — no full pack)."""

    projects: int = 0
    repos_total: int = 0
    repos_present: int = 0
    repos_missing: int = 0


class DiscoveryHealthRollup(BaseModel):
    """Maintenance health rollup for summary payloads."""

    ok: bool = True
    critical_count: int = 0
    warning_count: int = 0
    top_actions: list[str] = Field(default_factory=list)


class AgentSurfaceStats(BaseModel):
    """Agent onboarding artifact probes (umbrella + managed repos)."""

    manifest_has_agent_instructions: bool = False
    umbrella_has_agents_md: bool = False
    umbrella_has_llms_txt: bool = False
    repos_audited: int = 0
    repos_with_agents_md: int = 0
    repos_with_llms_txt: int = 0
    repos_with_readme_marker: int = 0
    repos_with_any_surface: int = 0


class CoordinationHints(BaseModel):
    """Lightweight AOS / ACL / task-graph hints when cheap to collect."""

    available: bool = False
    acl_leases_active: int = 0
    ready_tasks: int = 0
    doctor_findings: int = 0


class CoverageHints(BaseModel):
    """Optional cheap CI / semantic coverage signals."""

    repos_with_ci: int = 0
    repos_total: int = 0
    semantic_concepts: Optional[int] = None
    semantic_available: bool = False


class ReadinessDimension(BaseModel):
    """Single weighted readiness dimension."""

    score: int = 0
    weight: float = 0.25
    met: bool = False


class ReadinessBlocker(BaseModel):
    """Explainable readiness blocker for automation."""

    code: str
    severity: Literal["info", "warning", "critical"] = "warning"
    message: str
    project_name: Optional[str] = None
    repo_name: Optional[str] = None


class ReadinessScore(BaseModel):
    """Composite 0–100 readiness with dimension breakdown."""

    score: int = 0
    grade: Literal["excellent", "good", "fair", "poor"] = "poor"
    dimensions: dict[str, ReadinessDimension] = Field(default_factory=dict)
    blockers: list[ReadinessBlocker] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)


class WorkspaceSummaryResult(BaseModel):
    """Unified discovery + readiness payload for agents."""

    generated_at: str = ""
    workspace_root: str = ""
    gate: DiscoveryGateStatus
    map: DiscoveryMapStats = Field(default_factory=DiscoveryMapStats)
    health: DiscoveryHealthRollup = Field(default_factory=DiscoveryHealthRollup)
    agent_surfaces: AgentSurfaceStats = Field(default_factory=AgentSurfaceStats)
    coordination: CoordinationHints = Field(default_factory=CoordinationHints)
    coverage: CoverageHints = Field(default_factory=CoverageHints)
    readiness: ReadinessScore = Field(default_factory=ReadinessScore)
    quickstart_uri: str = "docs/agents-quickstart.md"
    cards: Optional[list[dict[str, Any]]] = None
