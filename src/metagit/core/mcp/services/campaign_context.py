#!/usr/bin/env python
"""MCP adapter for provenance-aware campaign context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from metagit.core.appconfig.models import AppConfig
from metagit.core.campaign.context import CampaignContextService
from metagit.core.campaign.service import CampaignService
from metagit.core.campaign.settings import everroom_settings_from_appconfig
from metagit.core.config.models import MetagitConfig


def resolve_campaign_context_payload(
    *,
    config: MetagitConfig,
    definition_root: str,
    workspace_root: str,
    slug: str,
    include: Optional[list[str]] = None,
    appconfig: Optional[AppConfig] = None,
) -> dict[str, Any]:
    """Assemble campaign context for MCP without exposing EverRoom credentials."""
    settings = everroom_settings_from_appconfig(appconfig)
    campaigns = CampaignService(
        config=config,
        definition_root=Path(definition_root),
        workspace_root=Path(workspace_root),
        campaigns_path=None,
    )
    service = CampaignContextService(
        campaign_service=campaigns,
        config=config,
        workspace_root=Path(workspace_root),
        definition_root=Path(definition_root),
        endpoint=settings.endpoint,
        token=settings.token,
        timeout_seconds=settings.timeout_seconds,
    )
    result = service.resolve(slug, include=include)
    return result.model_dump(mode="json")
