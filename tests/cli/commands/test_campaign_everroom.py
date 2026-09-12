#!/usr/bin/env python
"""CLI tests for campaign context and EverRoom subcommands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.campaign.models import CampaignContextProviderConfig
from metagit.core.campaign.service import CampaignService
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject
from tests.core.integrations.everroom.mock_gateway import (
    ROOM_ID,
    SECRET_TOKEN,
    start_mock_gateway,
)

_WORKSPACE_YML = """
name: workspace
kind: application
workspace:
  projects:
    - name: demo
      repos:
        - name: terraform-network
          url: https://github.com/org/terraform-network.git
"""


def _write_workspace(tmp_path: Path) -> Path:
    definition = tmp_path / ".metagit.yml"
    definition.write_text(_WORKSPACE_YML.strip() + "\n", encoding="utf-8")
    config = MetagitConfig(
        name="workspace",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[ProjectPath(name="terraform-network", url="https://github.com/org/terraform-network.git")],
                ),
            ],
        ),
    )
    service = CampaignService(config=config, definition_root=tmp_path)
    service.create(
        slug="terraform-hcp-migration",
        title="HCP migration",
        repos=["demo/terraform-network"],
        goal="Migrate Terraform from HCP to self-hosted",
    )
    return definition


def test_campaign_context_metagit_only_json(tmp_path: Path) -> None:
    definition = _write_workspace(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["campaign", "context", "--slug", "terraform-hcp-migration", "--definition", str(definition), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["campaign"]["id"] == "terraform-hcp-migration"
    assert payload["everroom"]["status"] == "NOT_CONFIGURED"
    assert payload["metagit"]["source"] == "metagit"
    assert SECRET_TOKEN not in result.output


def test_campaign_everroom_status_not_configured(tmp_path: Path) -> None:
    definition = _write_workspace(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["campaign", "everroom", "status", "--slug", "terraform-hcp-migration", "--definition", str(definition), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["everroom"]["status"] == "NOT_CONFIGURED"
    assert "MetaGit" in runner.invoke(
        cli,
        ["campaign", "everroom", "status", "--slug", "terraform-hcp-migration", "--definition", str(definition)],
    ).output


def test_campaign_everroom_attach_detach_sync(tmp_path: Path, monkeypatch) -> None:
    definition = _write_workspace(tmp_path)
    gateway = start_mock_gateway()
    monkeypatch.setenv("METAGIT_EVERROOM_URL", gateway.url)
    monkeypatch.setenv("METAGIT_EVERROOM_TOKEN", SECRET_TOKEN)
    runner = CliRunner()
    try:
        attach = runner.invoke(
            cli,
            [
                "campaign",
                "everroom",
                "attach",
                "--slug",
                "terraform-hcp-migration",
                "--room",
                ROOM_ID,
                "--definition",
                str(definition),
                "--json",
            ],
        )
        assert attach.exit_code == 0, attach.output
        attached = json.loads(attach.output)
        assert attached["room_id"] == ROOM_ID
        assert SECRET_TOKEN not in attach.output
        yaml_text = (tmp_path / "_campaigns" / "terraform-hcp-migration.yml").read_text(encoding="utf-8")
        assert SECRET_TOKEN not in yaml_text
        assert ROOM_ID in yaml_text

        status = runner.invoke(
            cli,
            [
                "campaign",
                "everroom",
                "status",
                "--slug",
                "terraform-hcp-migration",
                "--definition",
                str(definition),
                "--json",
            ],
        )
        assert status.exit_code == 0, status.output
        assert json.loads(status.output)["everroom"]["status"] == "AVAILABLE"

        context = runner.invoke(
            cli,
            [
                "campaign",
                "context",
                "--slug",
                "terraform-hcp-migration",
                "--definition",
                str(definition),
                "--json",
            ],
        )
        assert context.exit_code == 0, context.output
        packet = json.loads(context.output)
        assert packet["everroom"]["status"] == "AVAILABLE"
        assert packet["everroom"]["source_count"] == 4
        assert packet["everroom"]["decision_count"] == 3
        assert SECRET_TOKEN not in context.output

        sync = runner.invoke(
            cli,
            [
                "campaign",
                "everroom",
                "sync",
                "--slug",
                "terraform-hcp-migration",
                "--definition",
                str(definition),
                "--json",
            ],
        )
        assert sync.exit_code == 0, sync.output
        synced = json.loads(sync.output)
        assert synced["generated"] is True
        assert SECRET_TOKEN not in sync.output

        detach = runner.invoke(
            cli,
            [
                "campaign",
                "everroom",
                "detach",
                "--slug",
                "terraform-hcp-migration",
                "--definition",
                str(definition),
                "--json",
            ],
        )
        assert detach.exit_code == 0, detach.output
        assert json.loads(detach.output)["room_deleted"] is False
    finally:
        gateway.stop()


def test_campaign_everroom_sync_fails_when_unavailable(tmp_path: Path, monkeypatch) -> None:
    definition = _write_workspace(tmp_path)
    config = MetagitConfig(
        name="workspace",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[ProjectPath(name="terraform-network", url="https://github.com/org/terraform-network.git")],
                ),
            ],
        ),
    )
    CampaignService(config=config, definition_root=tmp_path).upsert_context_provider(
        "terraform-hcp-migration",
        CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint="http://127.0.0.1:1"),
    )
    monkeypatch.setenv("METAGIT_EVERROOM_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("METAGIT_EVERROOM_TOKEN", SECRET_TOKEN)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["campaign", "everroom", "sync", "--slug", "terraform-hcp-migration", "--definition", str(definition)],
    )
    assert result.exit_code != 0
    assert SECRET_TOKEN not in result.output


def test_campaign_context_warns_when_gateway_down(tmp_path: Path, monkeypatch) -> None:
    definition = _write_workspace(tmp_path)
    config = MetagitConfig(
        name="workspace",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[ProjectPath(name="terraform-network", url="https://github.com/org/terraform-network.git")],
                ),
            ],
        ),
    )
    CampaignService(config=config, definition_root=tmp_path).upsert_context_provider(
        "terraform-hcp-migration",
        CampaignContextProviderConfig(type="everroom", room_id=ROOM_ID, endpoint="http://127.0.0.1:1"),
    )
    monkeypatch.setenv("METAGIT_EVERROOM_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("METAGIT_EVERROOM_TOKEN", SECRET_TOKEN)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["campaign", "context", "--slug", "terraform-hcp-migration", "--definition", str(definition), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["metagit"]["repository_count"] == 1
    assert payload["everroom"]["status"] == "UNAVAILABLE"
    assert SECRET_TOKEN not in result.output
