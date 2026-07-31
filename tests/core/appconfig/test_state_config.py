#!/usr/bin/env python
"""Tests for state backend app-config wiring."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from unittest.mock import patch

from metagit.core.appconfig.models import AppConfig, StateConfig, StateMongoConfig
from metagit.core.context.models import Objective
from metagit.core.state.identity import resolve_org_id, resolve_workspace_id
from metagit.core.state.remote import RemoteHttpBackend
from metagit.core.state.resolver import resolve_backend
from metagit.core.web.config_preview import redact_secrets


def test_default_state_config_is_local() -> None:
    config = AppConfig()
    assert config.state.backend == "local"
    assert config.state.url == ""
    bundle = resolve_backend("/tmp/unused")
    objectives: list[Objective] = bundle.objectives().load()[0]
    assert objectives == []


def test_state_url_env_selects_remote_bundle() -> None:
    with patch.dict(os.environ, {"METAGIT_STATE_URL": "http://127.0.0.1:8787"}, clear=False):
        bundle = resolve_backend("/tmp/unused")
        backend = bundle.objectives()
        assert isinstance(getattr(backend, "_backend", None), RemoteHttpBackend)


def test_state_env_overrides_config_fields() -> None:
    config = AppConfig()
    with patch.dict(
        os.environ,
        {
            "METAGIT_STATE_URL": "http://example.test",
            "METAGIT_STATE_BACKEND": "http",
            "METAGIT_STATE_TOKEN": "secret-token",
        },
        clear=False,
    ):
        updated = AppConfig._override_from_environment(config)
    assert updated.state.url == "http://example.test"
    assert updated.state.backend == "http"
    assert updated.state.token == "secret-token"


def test_appconfig_preview_redacts_state_token() -> None:
    config = AppConfig(state=StateConfig(token="super-secret-token"))
    redacted = redact_secrets(config.model_dump(mode="json"))
    assert redacted["state"]["token"] == "***oken"


def test_state_config_accepts_plane_backends() -> None:
    config = StateConfig(backend="dynamodb", org_id="acme", workspace_id="ws1")
    assert config.backend == "dynamodb"
    assert config.dynamodb.table == ""
    assert config.mongodb.collection == "metagit_state"


def test_state_plane_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_STATE_ORG_ID", "acme")
    monkeypatch.setenv("METAGIT_STATE_WORKSPACE_ID", "platform")
    monkeypatch.setenv("METAGIT_STATE_DDB_TABLE", "state-table")
    monkeypatch.setenv("METAGIT_STATE_DDB_REGION", "us-east-1")
    monkeypatch.setenv("METAGIT_STATE_DDB_ENDPOINT", "http://localhost:8000")
    monkeypatch.setenv("METAGIT_STATE_MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("METAGIT_STATE_MONGO_DB", "metagit")

    updated = AppConfig._override_from_environment(AppConfig())

    assert updated.state.org_id == "acme"
    assert updated.state.workspace_id == "platform"
    assert updated.state.dynamodb.table == "state-table"
    assert updated.state.dynamodb.region == "us-east-1"
    assert updated.state.dynamodb.endpoint_url == "http://localhost:8000"
    assert updated.state.mongodb.uri == "mongodb://localhost:27017"
    assert updated.state.mongodb.database == "metagit"


def test_state_identity_resolution_uses_configured_values(tmp_path) -> None:
    state = StateConfig(org_id="acme", workspace_id="platform")
    assert resolve_org_id(state) == "acme"
    assert resolve_workspace_id(state, str(tmp_path)) == "platform"


def test_state_identity_resolution_derives_defaults(tmp_path) -> None:
    state = StateConfig()
    resolved_root = str(Path(tmp_path).resolve())
    expected_workspace_id = hashlib.sha256(resolved_root.encode("utf-8")).hexdigest()[:16]
    assert resolve_org_id(state) == "_"
    assert resolve_workspace_id(state, str(tmp_path)) == expected_workspace_id


def test_preview_redacts_mongo_uri() -> None:
    config = AppConfig(state=StateConfig(mongodb=StateMongoConfig(uri="mongodb://user:pass@host/db")))
    redacted = redact_secrets(config.model_dump(mode="json"))
    assert "pass" not in redacted["state"]["mongodb"]["uri"]


def test_describe_state_backend_defaults_local() -> None:
    from metagit.core.state.resolver import describe_state_backend

    info = describe_state_backend("/tmp/ws")
    assert info["backend"] == "local"
    assert info["url"] == ""
    assert info["token_configured"] is False


def test_describe_state_backend_reports_remote_env(monkeypatch) -> None:
    from metagit.core.state.resolver import describe_state_backend

    monkeypatch.setenv("METAGIT_STATE_URL", "http://127.0.0.1:8787")
    monkeypatch.setenv("METAGIT_STATE_TOKEN", "secret")
    info = describe_state_backend("/tmp/ws")
    assert info["backend"] == "http"
    assert info["url"] == "http://127.0.0.1:8787"
    assert info["env_overrides"]["METAGIT_STATE_URL"] is True
    assert info["token_configured"] is True
