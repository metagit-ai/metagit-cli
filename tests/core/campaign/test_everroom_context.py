#!/usr/bin/env python
"""Campaign context assembly: MetaGit-only, EverRoom, degraded, provenance."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.campaign.context import CampaignContextService, generated_document_markdown
from metagit.core.campaign.context_models import CONTEXT_SCHEMA_VERSION, ContextLimits
from metagit.core.campaign.models import CampaignContextProviderConfig
from metagit.core.campaign.service import CampaignService
from metagit.core.component.models import Component
from metagit.core.config.graph_models import GraphEndpoint, GraphRelationship, WorkspaceGraph
from metagit.core.config.models import MetagitConfig
from metagit.core.integrations.everroom.errors import (
    EverRoomAuthError,
    EverRoomInvalidResponseError,
    EverRoomNotFoundError,
    EverRoomUnavailableError,
)
from metagit.core.integrations.everroom.models import EverRoomSource
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject
from tests.core.integrations.everroom.fakes import FakeEverRoomClient
from tests.core.integrations.everroom.mock_gateway import ROOM_ID, SECRET_TOKEN


def _config_with_urls() -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[
                        ProjectPath(name="terraform-network", url="https://github.com/org/terraform-network.git"),
                        ProjectPath(name="orphan", url="https://github.com/org/unmapped.git"),
                    ],
                ),
            ],
        ),
        graph=WorkspaceGraph(
            relationships=[
                GraphRelationship(
                    id="rel-1",
                    from_endpoint=GraphEndpoint(project="demo", repo="terraform-network"),
                    to=GraphEndpoint(project="demo", repo="orphan"),
                    type="depends_on",
                    label="network depends on accounts",
                ),
            ],
        ),
    )


def _service(tmp_path: Path, config: MetagitConfig, client: FakeEverRoomClient | None = None) -> tuple[CampaignService, CampaignContextService]:
    campaigns = CampaignService(config=config, definition_root=tmp_path)
    context = CampaignContextService(
        campaign_service=campaigns,
        config=config,
        workspace_root=tmp_path,
        definition_root=tmp_path,
        token=SECRET_TOKEN,
        client=client,
    )
    return campaigns, context


def test_metagit_only_context(tmp_path: Path) -> None:
    config = _config_with_urls()
    campaigns, context = _service(tmp_path, config)
    campaigns.create(
        slug="terraform-hcp-migration",
        title="HCP migration",
        repos=["demo/terraform-network"],
        goal="Migrate Terraform from HCP to self-hosted",
    )
    packet = context.resolve("terraform-hcp-migration")
    assert packet.context_schema_version == CONTEXT_SCHEMA_VERSION
    assert packet.campaign.source == "metagit"
    assert packet.metagit.source == "metagit"
    assert packet.everroom.source == "everroom"
    assert packet.everroom.status == "NOT_CONFIGURED"
    assert packet.metagit.repository_count == 1
    assert any(item.source == "metagit" for item in packet.provenance)
    assert not any(item.source == "everroom" for item in packet.provenance)
    dumped = json.dumps(packet.model_dump(mode="json"))
    assert SECRET_TOKEN not in dumped


def test_metagit_plus_everroom_context(tmp_path: Path) -> None:
    config = _config_with_urls()
    fake = FakeEverRoomClient()
    campaigns, context = _service(tmp_path, config, fake)
    campaigns.create(
        slug="terraform-hcp-migration",
        title="HCP migration",
        repos=["demo/terraform-network", "demo/orphan"],
        goal="Migrate Terraform from HCP to self-hosted",
    )
    campaigns.upsert_context_provider(
        "terraform-hcp-migration",
        CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint="http://127.0.0.1:3210"),
    )
    packet = context.resolve("terraform-hcp-migration")
    assert packet.everroom.status == "AVAILABLE"
    assert packet.everroom.source_count == 4
    assert packet.everroom.decision_count == 3
    assert packet.everroom.document_count == 2
    assert packet.everroom.open_question_count == 2
    mapped = next(repo for repo in packet.metagit.repositories if repo.repo == "terraform-network")
    orphan = next(repo for repo in packet.metagit.repositories if repo.repo == "orphan")
    assert mapped.mapping == "mapped"
    assert mapped.everroom_source == "src-network"
    assert orphan.mapping == "unmapped"
    assert packet.metagit.relationship_count == 1
    assert any(item.source == "everroom" for item in packet.provenance)
    for decision in packet.everroom.decisions:
        assert decision.get("source") == "everroom"
    dumped = json.dumps(packet.model_dump(mode="json"))
    assert SECRET_TOKEN not in dumped
    markdown = generated_document_markdown(packet)
    assert "Generated by MetaGit" in markdown
    assert SECRET_TOKEN not in markdown
    assert packet.campaign.id in markdown


def test_everroom_unavailable_degrades_to_metagit(tmp_path: Path) -> None:
    config = _config_with_urls()
    fake = FakeEverRoomClient(error=EverRoomUnavailableError("EverRoom Gateway is unavailable (connection refused)"))
    campaigns, context = _service(tmp_path, config, fake)
    campaigns.create(slug="c1", title="C1", repos=["demo/terraform-network"], goal="goal")
    campaigns.upsert_context_provider(
        "c1",
        CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint="http://127.0.0.1:3210"),
    )
    packet = context.resolve("c1")
    assert packet.metagit.repository_count == 1
    assert packet.everroom.status == "UNAVAILABLE"
    assert packet.warnings
    assert "MetaGit-only" in packet.warnings[0]


def test_auth_failure_is_explicit(tmp_path: Path) -> None:
    config = _config_with_urls()
    fake = FakeEverRoomClient(
        error=EverRoomAuthError(
            "EverRoom authentication failed: set METAGIT_EVERROOM_TOKEN "
            "(do not store the token in campaign YAML or Git).",
        ),
    )
    campaigns, context = _service(tmp_path, config, fake)
    campaigns.create(slug="c1", title="C1", repos=["demo/terraform-network"])
    campaigns.upsert_context_provider(
        "c1",
        CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint="http://127.0.0.1:3210"),
    )
    packet = context.resolve("c1")
    assert packet.everroom.status == "AUTH_FAILED"
    assert "METAGIT_EVERROOM_TOKEN" in (packet.warnings[0] if packet.warnings else "")
    assert SECRET_TOKEN not in json.dumps(packet.model_dump(mode="json"))


def test_room_missing_degrades(tmp_path: Path) -> None:
    config = _config_with_urls()
    fake = FakeEverRoomClient(error=EverRoomNotFoundError("EverRoom Room not found: stale"))
    campaigns, context = _service(tmp_path, config, fake)
    campaigns.create(slug="c1", title="C1", repos=["demo/terraform-network"])
    campaigns.upsert_context_provider(
        "c1",
        CampaignContextProviderConfig(type="everroom", room_id="stale", endpoint="http://127.0.0.1:3210"),
    )
    packet = context.resolve("c1")
    assert packet.everroom.status == "ROOM_NOT_FOUND"
    assert packet.metagit.repository_count == 1


def test_partial_everroom_response(tmp_path: Path) -> None:
    config = _config_with_urls()
    fake = FakeEverRoomClient()
    fake.method_errors["list_room_decisions"] = EverRoomInvalidResponseError("bad decisions")
    fake.method_errors["list_room_sources"] = EverRoomUnavailableError("files down")
    campaigns, context = _service(tmp_path, config, fake)
    campaigns.create(slug="c1", title="C1", repos=["demo/terraform-network"])
    campaigns.upsert_context_provider(
        "c1",
        CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint="http://127.0.0.1:3210"),
    )
    packet = context.resolve("c1")
    assert packet.everroom.status == "AVAILABLE"
    assert packet.everroom.decisions == []
    assert packet.everroom.sources == []
    assert packet.everroom.open_question_count == 2


def test_empty_room(tmp_path: Path) -> None:
    config = _config_with_urls()
    fake = FakeEverRoomClient(
        fixture={
            "room": {"id": ROOM_ID, "title": "empty"},
            "context": {
                "roomId": ROOM_ID,
                "overview": "",
                "status": "",
                "nextSteps": [],
                "actionItems": [],
            },
            "sources": [],
            "decisions": [],
            "documents": [],
            "wiki": [],
            "materials": [],
        },
    )
    campaigns, context = _service(tmp_path, config, fake)
    campaigns.create(slug="c1", title="C1", repos=["demo/terraform-network"])
    campaigns.upsert_context_provider(
        "c1",
        CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint="http://127.0.0.1:3210"),
    )
    packet = context.resolve("c1")
    assert packet.everroom.status == "AVAILABLE"
    assert packet.everroom.source_count == 0
    assert packet.everroom.decision_count == 0
    assert packet.everroom.open_question_count == 0


def test_large_context_is_capped(tmp_path: Path) -> None:
    extras = [
        EverRoomSource(id=f"src-{idx}", title=f"file-{idx}", originalName=f"file-{idx}.md")
        for idx in range(40)
    ]
    fake = FakeEverRoomClient(extra_sources=extras)
    config = _config_with_urls()
    campaigns, context = _service(tmp_path, config, fake)
    campaigns.create(slug="c1", title="C1", repos=["demo/terraform-network"])
    campaigns.upsert_context_provider(
        "c1",
        CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint="http://127.0.0.1:3210"),
    )
    packet = context.resolve("c1", limits=ContextLimits(sources=20, decisions=8))
    assert packet.everroom.source_count == 44
    assert len(packet.everroom.sources) == 20
    assert len(packet.everroom.decisions) <= 8


def test_components_included_from_catalog(tmp_path: Path) -> None:
    config = MetagitConfig(
        name="ws",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[
                        ProjectPath(
                            name="terraform-network",
                            url="https://github.com/org/terraform-network.git",
                            components=[Component(name="tgw", path="modules/tgw")],
                        ),
                    ],
                ),
            ],
        ),
    )
    campaigns, context = _service(tmp_path, config)
    campaigns.create(slug="c1", title="C1", repos=["demo/terraform-network"])
    packet = context.resolve("c1")
    assert "demo/terraform-network/tgw" in packet.metagit.components
