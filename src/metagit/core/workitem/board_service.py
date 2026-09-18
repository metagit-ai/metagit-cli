#!/usr/bin/env python
"""Bind campaign overlays to Azure DevOps (or similar) work items in pages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from metagit.core.campaign.service import CampaignService
from metagit.core.context.reduction import DEFAULT_CAMPAIGN_EXPAND_LIMIT, page_rows
from metagit.core.workitem.azure_devops import AzureDevOpsBoardClient
from metagit.core.workitem.models import ExternalWorkRef
from metagit.core.workitem.protocol import BoardProvider


class CampaignBoardSyncResult(BaseModel):
    """Paged board-sync outcome — never dumps the full campaign repo list."""

    ok: bool = True
    slug: str
    provider: str = "azure_devops"
    parent: Optional[ExternalWorkRef] = None
    created: list[ExternalWorkRef] = Field(default_factory=list)
    skipped: int = 0
    matched_count: int = 0
    truncated: bool = False
    offset: int = 0
    limit: Optional[int] = None
    dry_run: bool = False
    error: Optional[str] = None


class CampaignBoardService:
    """Create a parent work item plus paged child items for campaign repos."""

    def __init__(
        self,
        *,
        campaign_service: CampaignService,
        client: BoardProvider,
        provider_name: str = "azure_devops",
    ) -> None:
        self._campaigns = campaign_service
        self._client = client
        self._provider_name = provider_name

    def sync(
        self,
        *,
        slug: str,
        parent_kind: str = "Feature",
        child_kind: str = "User Story",
        limit: Optional[int] = DEFAULT_CAMPAIGN_EXPAND_LIMIT,
        offset: int = 0,
        dry_run: bool = False,
    ) -> CampaignBoardSyncResult:
        campaign = self._campaigns.load(slug)
        if campaign is None:
            return CampaignBoardSyncResult(
                ok=False,
                slug=slug,
                error=f"Unknown campaign: {slug!r}",
            )
        paged, truncated = page_rows(campaign.repos, limit=limit, offset=offset)
        parent = campaign.work_item
        created: list[ExternalWorkRef] = []
        skipped = 0
        if dry_run:
            pending_children = [row for row in paged if row.work_item is None]
            skipped = len(paged) - len(pending_children)
            return CampaignBoardSyncResult(
                ok=True,
                slug=slug,
                provider=self._provider_name,
                parent=parent,
                created=[],
                skipped=skipped,
                matched_count=len(campaign.repos),
                truncated=truncated,
                offset=max(offset, 0),
                limit=limit,
                dry_run=True,
            )

        if parent is None:
            created_parent = self._client.create_item(
                title=campaign.title,
                description=campaign.goal or f"Campaign {campaign.slug}",
                kind=parent_kind,
            )
            if isinstance(created_parent, Exception):
                return CampaignBoardSyncResult(
                    ok=False,
                    slug=slug,
                    error=str(created_parent),
                    matched_count=len(campaign.repos),
                    truncated=truncated,
                    offset=max(offset, 0),
                    limit=limit,
                )
            parent = created_parent
            campaign.work_item = parent
            created.append(parent)

        for row in paged:
            if row.work_item is not None:
                skipped += 1
                continue
            child = self._client.create_item(
                title=f"{campaign.title}: {row.project}/{row.repo}",
                description=f"Campaign {campaign.slug} repo {row.project}/{row.repo}",
                kind=child_kind,
                parent=parent,
            )
            if isinstance(child, Exception):
                return CampaignBoardSyncResult(
                    ok=False,
                    slug=slug,
                    parent=parent,
                    created=created,
                    skipped=skipped,
                    matched_count=len(campaign.repos),
                    truncated=truncated,
                    offset=max(offset, 0),
                    limit=limit,
                    error=str(child),
                )
            row.work_item = child
            created.append(child)

        campaign.updated = datetime.now(timezone.utc).isoformat()
        self._campaigns._save(campaign)
        return CampaignBoardSyncResult(
            ok=True,
            slug=slug,
            provider=self._provider_name,
            parent=parent,
            created=created,
            skipped=skipped,
            matched_count=len(campaign.repos),
            truncated=truncated,
            offset=max(offset, 0),
            limit=limit,
            dry_run=False,
        )


def azure_board_client_from_appconfig(
    *,
    api_token: str,
    organization: str,
    project: str,
    base_url: str,
) -> AzureDevOpsBoardClient:
    """Construct the ADO WIT client from resolved AppConfig / CLI values."""
    return AzureDevOpsBoardClient(
        api_token=api_token,
        organization=organization,
        project=project,
        base_url=base_url,
    )


__all__ = [
    "CampaignBoardService",
    "CampaignBoardSyncResult",
    "azure_board_client_from_appconfig",
]
