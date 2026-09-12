#!/usr/bin/env python
"""Integration tests for campaign context against a mock EverRoom Gateway."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from metagit.core.campaign.context import CampaignContextService
from metagit.core.campaign.everroom_service import CampaignEverRoomService, EverRoomSettings
from metagit.core.campaign.models import CampaignContextProviderConfig
from metagit.core.campaign.service import CampaignService
from metagit.core.config.models import MetagitConfig
from metagit.core.integrations.everroom.client import EverRoomHttpClient
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject
from tests.core.integrations.everroom.mock_gateway import (
    ROOM_ID,
    SECRET_TOKEN,
    start_mock_gateway,
)


def _config() -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[
                        ProjectPath(name="terraform-network", url="https://github.com/org/terraform-network.git"),
                        ProjectPath(name="terraform-org", url="https://github.com/org/terraform-org.git"),
                    ],
                ),
            ],
        ),
    )


def test_mock_gateway_campaign_context_packet(tmp_path: Path) -> None:
    gateway = start_mock_gateway()
    try:
        config = _config()
        campaigns = CampaignService(config=config, definition_root=tmp_path)
        campaigns.create(
            slug="terraform-hcp-migration",
            title="HCP migration",
            repos=["demo/terraform-network", "demo/terraform-org"],
            goal="Migrate Terraform from HCP to self-hosted",
        )
        campaigns.upsert_context_provider(
            "terraform-hcp-migration",
            CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint=gateway.url),
        )
        client = EverRoomHttpClient(endpoint=gateway.url, token=SECRET_TOKEN)
        context = CampaignContextService(
            campaign_service=campaigns,
            config=config,
            workspace_root=tmp_path,
            definition_root=tmp_path,
            endpoint=gateway.url,
            token=SECRET_TOKEN,
            client=client,
        )
        packet = context.resolve("terraform-hcp-migration")
        assert packet.everroom.status == "AVAILABLE"
        assert packet.everroom.room_id == ROOM_ID
        assert packet.everroom.source_count == 4
        assert packet.everroom.decision_count == 3
        assert packet.everroom.document_count == 2
        assert packet.everroom.open_question_count == 2
        network = next(repo for repo in packet.metagit.repositories if repo.repo == "terraform-network")
        assert network.mapping == "mapped"
        dumped = json.dumps(packet.model_dump(mode="json"))
        assert SECRET_TOKEN not in dumped
        service = CampaignEverRoomService(
            campaign_service=campaigns,
            context_service=context,
            settings=EverRoomSettings(endpoint=gateway.url, token=SECRET_TOKEN),
            client=client,
        )
        synced = service.sync("terraform-hcp-migration")
        assert synced.generated is True
        assert SECRET_TOKEN not in synced.document_id
    finally:
        gateway.stop()


@pytest.mark.skipif(os.getenv("METAGIT_EVERROOM_LIVE") != "1", reason="optional live EverRoom Gateway")
def test_optional_live_gateway_health() -> None:
    endpoint = os.getenv("METAGIT_EVERROOM_URL", "http://127.0.0.1:3210")
    token = os.getenv("METAGIT_EVERROOM_TOKEN", "")
    client = EverRoomHttpClient(endpoint=endpoint, token=token, timeout_seconds=2.0)
    health = client.health()
    assert health.status == "ok"
