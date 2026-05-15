#!/usr/bin/env python
"""
Pydantic models for workspace health check results.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class HealthRecommendation(BaseModel):
    """Actionable workspace maintenance recommendation."""

    severity: Literal["info", "warning", "critical"] = "info"
    action: str
    message: str
    project_name: Optional[str] = None
    repo_name: Optional[str] = None
    repo_path: Optional[str] = None


class RepoHealthRow(BaseModel):
    """Per-repository health signals."""

    project_name: str
    repo_name: str
    repo_path: str
    status: str
    exists: bool
    is_git_repo: bool
    branch: Optional[str] = None
    dirty: Optional[bool] = None
    ahead: Optional[int] = None
    behind: Optional[int] = None
    gitnexus_status: Optional[str] = None
    head_commit_age_days: Optional[float] = None
    merge_base_age_days: Optional[float] = None


class WorkspaceHealthResult(BaseModel):
    """Aggregate workspace health report."""

    ok: bool = True
    workspace_root: str = ""
    summary: dict[str, int] = Field(default_factory=dict)
    repos: list[RepoHealthRow] = Field(default_factory=list)
    recommendations: list[HealthRecommendation] = Field(default_factory=list)
