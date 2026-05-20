#!/usr/bin/env python
"""Tests for appconfig show display and agent_mode."""

import os

from metagit.core.appconfig.agent_mode import resolve_agent_mode
from metagit.core.appconfig.display import build_appconfig_payload, render_appconfig_show
from metagit.core.appconfig.models import AppConfig


def test_appconfig_show_includes_dedupe_and_agent_mode() -> None:
    config = AppConfig()
    payload = build_appconfig_payload(config, config_path="/tmp/metagit.config.yaml")
    assert payload["agent_mode"] is False
    assert payload["config"]["workspace"]["dedupe"]["enabled"] is True


def test_metagit_agent_mode_env_overrides_config(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_AGENT_MODE", "true")
    config = AppConfig(agent_mode=False)
    config = AppConfig._override_from_environment(config)
    assert resolve_agent_mode(config) is True


def test_render_appconfig_show_json() -> None:
    rendered = render_appconfig_show(
        AppConfig(),
        config_path="metagit.config.yaml",
        output_format="json",
    )
    assert '"agent_mode"' in rendered
    assert '"dedupe"' in rendered
