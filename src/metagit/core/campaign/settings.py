#!/usr/bin/env python
"""Resolve EverRoom Gateway settings from AppConfig plus environment."""

from __future__ import annotations

from typing import Optional

from metagit.core.appconfig.models import AppConfig, EverRoomConfig
from metagit.core.campaign.everroom_service import EverRoomSettings


def everroom_settings_from_appconfig(appconfig: Optional[AppConfig]) -> EverRoomSettings:
    """CLI/env/appconfig defaults. Campaign YAML still owns the Room id."""
    block: EverRoomConfig = appconfig.everroom if appconfig is not None else EverRoomConfig()
    return EverRoomSettings(
        endpoint=block.endpoint or "http://127.0.0.1:3210",
        token=block.token or "",
        timeout_seconds=block.timeout_seconds,
    )
