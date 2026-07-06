#!/usr/bin/env python
"""Pydantic models for native workspace campaigns."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

CampaignStatus = Literal["draft", "active", "completed", "archived"]
CampaignRepoStatus = Literal["pending", "routed", "mr-open", "merged", "blocked"]


class CampaignSelection(BaseModel):
    """How repos were chosen for a campaign."""

    query: Optional[str] = Field(default=None, description="Original metagit find query")
    tags: dict[str, str] = Field(default_factory=dict, description="Tag filters used during selection")
    resolved_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when repos[] was frozen",
    )


class CampaignRepoEntry(BaseModel):
    """One repository tracked by a campaign."""

    project: str
    repo: str
    role: Optional[str] = Field(default=None, description="Optional role label within the campaign")
    status: CampaignRepoStatus = Field(default="pending")
    mr: Optional[str] = Field(default=None, description="Merge request or pull request URL")
    note: Optional[str] = Field(default=None, description="Free-form status note")


class CampaignLesson(BaseModel):
    """Captured lesson learned during a campaign."""

    text: str
    recorded_at: Optional[str] = Field(default=None, description="ISO timestamp")


class CampaignDocument(BaseModel):
    """On-disk campaign overlay committed under the configured campaigns directory."""

    schema_version: str = Field(default="1.0")
    slug: str
    title: str
    status: CampaignStatus = Field(default="draft")
    objective_id: Optional[str] = Field(
        default=None,
        description="Optional 1:1 spine objective id",
    )
    selection: CampaignSelection = Field(default_factory=CampaignSelection)
    repos: list[CampaignRepoEntry] = Field(default_factory=list)
    lessons: list[CampaignLesson] = Field(default_factory=list)


class CampaignListItem(BaseModel):
    """Summary row for campaign list."""

    slug: str
    title: str
    status: CampaignStatus
    repo_count: int
    merged_count: int
    open_mr_count: int
    blocked_count: int


class CampaignListResult(BaseModel):
    """All campaigns under the manifest root."""

    campaigns: list[CampaignListItem] = Field(default_factory=list)


class CampaignStatusResult(BaseModel):
    """Detailed campaign status rollup."""

    campaign: CampaignDocument
    merged_count: int
    open_mr_count: int
    blocked_count: int
    pending_count: int


class CampaignValidationIssue(BaseModel):
    """One validation failure for a campaign document."""

    slug: str
    message: str


class CampaignExpandResult(BaseModel):
    """Outcome when expanding a campaign into per-repo objectives."""

    slug: str
    objective_ids: list[str] = Field(default_factory=list)
    dry_run: bool = False
