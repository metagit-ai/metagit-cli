#!/usr/bin/env python
"""Pydantic models for inheritable agent_profile blocks in .metagit.yml."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.skills.installer import InstallResult


class AgentProfile(BaseModel):
    """Structured agent posture declared at workspace, project, or repo scope."""

    tier: Optional[str] = Field(
        default=None,
        description="Optional tier label (e.g. full, minimal); mirrors tags.agent_tier when unset",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Bundled skill ids to install for agents working in this scope",
    )
    mcp: list[str] = Field(
        default_factory=list,
        description="MCP server ids to configure (references only, never inline payloads)",
    )
    rules: list[str] = Field(
        default_factory=list,
        description="Rule ids to materialize into vendor rule directories",
    )
    vendors: list[str] = Field(
        default_factory=list,
        description="Vendor runtimes this profile targets (empty = all supported vendors)",
    )
    inherit: bool = Field(
        default=True,
        description="When true, merge with parent scope profile; when false, use verbatim",
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class AgentProfileLayer(BaseModel):
    """One resolved profile layer before merge."""

    scope: Literal["workspace", "project", "repo"]
    profile: AgentProfile


class EffectiveAgentProfile(BaseModel):
    """Fully merged agent profile for one repository."""

    project_name: str
    repo_name: str
    tier: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    mcp: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    vendors: list[str] = Field(default_factory=list)
    layers: list[AgentProfileLayer] = Field(default_factory=list)


class AgentProfileValidationIssue(BaseModel):
    """One catalog resolution failure for agent_profile references."""

    scope: str
    project: Optional[str] = None
    repo: Optional[str] = None
    field: str
    value: str
    message: str


class AgentApplyTargetResult(BaseModel):
    """Apply outcome for one repository clone."""

    project_name: str
    repo_name: str
    repo_path: str
    vendor: str
    applied: bool
    dry_run: bool
    details: list[str] = Field(default_factory=list)
    install_results: list[InstallResult] = Field(default_factory=list)


class AgentApplySummary(BaseModel):
    """Aggregate result for agent apply fan-out."""

    vendor: str
    dry_run: bool
    targets: list[AgentApplyTargetResult] = Field(default_factory=list)
