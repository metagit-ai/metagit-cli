#!/usr/bin/env python
"""Pydantic models for native workspace campaigns."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

CampaignStatus = Literal["draft", "active", "completed", "archived"]
CampaignRepoStatus = Literal["pending", "routed", "mr-open", "merged", "blocked"]

# Legacy status aliases accepted on load and normalized to the canonical enum.
# Supports overlays authored before the native schema existed (e.g. SRAM's
# ``task campaign:*`` layer which wrote ``complete`` instead of ``completed``).
_STATUS_ALIASES = {"complete": "completed", "done": "completed", "in-progress": "active"}


def _coerce_tags(value: Any) -> dict[str, str]:
    """Normalize a tag filter set to a dict.

    Legacy overlays wrote ``selection.tags`` as a list (often empty, or
    ``key=value`` strings). Native uses a dict. Accept both so pre-existing
    campaign documents load without a rewrite.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        parsed: dict[str, str] = {}
        for item in value:
            if isinstance(item, str) and "=" in item:
                key, val = item.split("=", 1)
                parsed[key] = val
        return parsed
    return {}


class CampaignSelection(BaseModel):
    """How repos were chosen for a campaign."""

    query: Optional[str] = Field(default=None, description="Original metagit find query")
    tags: dict[str, str] = Field(default_factory=dict, description="Tag filters used during selection")
    resolved_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when repos[] was frozen",
    )

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: Any) -> dict[str, str]:
        return _coerce_tags(value)


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
    goal: Optional[str] = Field(
        default=None,
        description="Free-text objective describing what the campaign delivers",
    )
    reference_impl: Optional[str] = Field(
        default=None,
        description="Exemplar repo (project/repo) to model other repos' changes on",
    )
    objective_id: Optional[str] = Field(
        default=None,
        description="Optional 1:1 spine objective id",
    )
    created: Optional[str] = Field(
        default=None,
        description="ISO date/timestamp the campaign was created",
    )
    updated: Optional[str] = Field(
        default=None,
        description="ISO date/timestamp the campaign was last modified",
    )
    selection: CampaignSelection = Field(default_factory=CampaignSelection)
    repos: list[CampaignRepoEntry] = Field(default_factory=list)
    lessons: list[CampaignLesson] = Field(default_factory=list)

    @field_validator("schema_version", mode="before")
    @classmethod
    def _coerce_schema_version(cls, value: Any) -> str:
        # Legacy overlays wrote an integer (schema_version: 1); native types it str.
        if value is None:
            return "1.0"
        return str(value)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return _STATUS_ALIASES.get(value, value)
        return value


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
