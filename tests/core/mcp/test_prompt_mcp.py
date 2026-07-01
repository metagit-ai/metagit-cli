#!/usr/bin/env python
"""Tests for MCP prompts/list and prompts/get handlers."""

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.prompt_mcp import get_mcp_prompt, list_mcp_prompts, parse_prompt_name


def test_list_mcp_prompts_includes_session_start() -> None:
    payload = list_mcp_prompts(active=True)
    names = [item["name"] for item in payload["prompts"]]
    assert "workspace/session-start" in names


def test_list_mcp_prompts_empty_when_inactive() -> None:
    payload = list_mcp_prompts(active=False)
    assert payload["prompts"] == []


def test_get_mcp_prompt_workspace_session_start() -> None:
    config = MetagitConfig(
        name="demo",
        kind="application",
        workspace={"projects": []},
    )
    payload = get_mcp_prompt(
        config=config,
        name="workspace/session-start",
        arguments={"instructions": "0"},
        config_path="/tmp/.metagit.yml",
        workspace_root="/tmp",
    )
    assert payload["messages"][0]["content"]["text"]
    assert payload["_meta"]["resource_uri"].startswith("metagit://prompt/workspace/session-start")


def test_parse_prompt_name() -> None:
    scope, kind = parse_prompt_name("repo/subagent-handoff")
    assert scope == "repo"
    assert kind == "subagent-handoff"
