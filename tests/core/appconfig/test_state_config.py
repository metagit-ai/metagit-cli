#!/usr/bin/env python
"""Tests for state backend app-config wiring."""

from __future__ import annotations

import os
from unittest.mock import patch

from metagit.core.appconfig.models import AppConfig, StateConfig
from metagit.core.state.remote import RemoteHttpBackend
from metagit.core.state.resolver import resolve_backend
from metagit.core.web.config_preview import redact_secrets


def test_default_state_config_is_local() -> None:
    config = AppConfig()
    assert config.state.backend == "local"
    assert config.state.url == ""
    bundle = resolve_backend("/tmp/unused")
    assert bundle.objectives().load()[0] == []


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
