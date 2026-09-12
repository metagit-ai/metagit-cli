#!/usr/bin/env python
"""EverRoom AppConfig and campaign provider configuration tests."""

from __future__ import annotations

from pathlib import Path

from metagit.core.appconfig.models import AppConfig, EverRoomConfig
from metagit.core.campaign.models import CampaignContextProviderConfig, CampaignDocument
from metagit.core.campaign.service import CampaignService
from metagit.core.campaign.settings import everroom_settings_from_appconfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.utils.yaml_class import yaml
from metagit.core.workspace.models import Workspace, WorkspaceProject
from tests.core.integrations.everroom.mock_gateway import SECRET_TOKEN


def _config() -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        workspace=Workspace(
            projects=[WorkspaceProject(name="demo", repos=[ProjectPath(name="alpha", path="./")])],
        ),
    )


def test_everroom_disabled_by_default() -> None:
    cfg = AppConfig()
    assert cfg.everroom.enabled is False
    assert cfg.everroom.endpoint == "http://127.0.0.1:3210"
    assert cfg.everroom.token == ""


def test_everroom_env_configuration(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_EVERROOM_ENABLED", "true")
    monkeypatch.setenv("METAGIT_EVERROOM_URL", "http://127.0.0.1:3999")
    monkeypatch.setenv("METAGIT_EVERROOM_TOKEN", SECRET_TOKEN)
    monkeypatch.setenv("METAGIT_EVERROOM_TIMEOUT", "3.5")
    loaded = AppConfig.load("/nonexistent/metagit-everroom-config.yml")
    assert isinstance(loaded, AppConfig)
    assert loaded.everroom.enabled is True
    assert loaded.everroom.endpoint == "http://127.0.0.1:3999"
    assert loaded.everroom.token == SECRET_TOKEN
    assert loaded.everroom.timeout_seconds == 3.5
    settings = everroom_settings_from_appconfig(loaded)
    assert settings.token == SECRET_TOKEN
    dumped = loaded.model_dump(mode="json")
    # Token may live in local appconfig objects but must not be treated as campaign YAML.
    assert "room_id" not in dumped["everroom"]


def test_missing_token_settings() -> None:
    settings = everroom_settings_from_appconfig(AppConfig(everroom=EverRoomConfig(endpoint="http://127.0.0.1:3210")))
    assert settings.token == ""


def test_invalid_timeout_env_ignored(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_EVERROOM_TIMEOUT", "not-a-float")
    loaded = AppConfig.load("/nonexistent/metagit-everroom-timeout.yml")
    assert isinstance(loaded, AppConfig)
    assert loaded.everroom.timeout_seconds == 8.0


def test_campaign_yaml_omits_empty_context_and_never_stores_token(tmp_path: Path) -> None:
    service = CampaignService(config=_config(), definition_root=tmp_path)
    campaign = service.create(slug="rollout", title="Rollout", repos=["demo/alpha"])
    text = (tmp_path / "_campaigns" / "rollout.yml").read_text(encoding="utf-8")
    assert "context:" not in text
    assert SECRET_TOKEN not in text
    service.upsert_context_provider(
        campaign.slug,
        CampaignContextProviderConfig(
            type="everroom",
            room_id="room_01JTESTMIGRATION",
            endpoint="http://127.0.0.1:3210",
        ),
    )
    stored = CampaignDocument.model_validate(
        yaml.safe_load((tmp_path / "_campaigns" / "rollout.yml").read_text(encoding="utf-8")),
    )
    provider = stored.everroom_provider()
    assert provider is not None
    assert provider.room_id == "room_01JTESTMIGRATION"
    yaml_text = (tmp_path / "_campaigns" / "rollout.yml").read_text(encoding="utf-8")
    assert "token" not in yaml_text
    assert SECRET_TOKEN not in yaml_text
    service.remove_context_provider("rollout", "everroom")
    after = (tmp_path / "_campaigns" / "rollout.yml").read_text(encoding="utf-8")
    assert "providers:" not in after
