#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.resource_catalog
"""

from metagit.core.mcp.models import McpActivationState
from metagit.core.mcp.resource_catalog import (
    build_catalog_payload,
    parse_project_summary_uri,
    parse_prompt_uri,
    parse_repo_card_uri,
    parse_resource_uri,
    query_bool,
)


def test_parse_prompt_uri() -> None:
    parsed = parse_resource_uri("metagit://prompt/workspace/session-start?instructions=0")
    target = parse_prompt_uri(parsed)
    assert target == ("workspace", "session-start")
    assert query_bool(parsed.query.get("instructions"), default=True) is False


def test_parse_project_summary_uri() -> None:
    parsed = parse_resource_uri("metagit://project/portfolio/summary")
    assert parse_project_summary_uri(parsed) == "portfolio"


def test_parse_repo_card_uri() -> None:
    parsed = parse_resource_uri("metagit://repo/portfolio/api/card")
    assert parse_repo_card_uri(parsed) == ("portfolio", "api")


def test_catalog_includes_dynamic_patterns_when_active() -> None:
    payload = build_catalog_payload(gate_state=McpActivationState.ACTIVE)
    assert payload.dynamic_patterns
    assert "metagit://catalog" in payload.read_order


def test_catalog_omits_active_resources_when_inactive() -> None:
    payload = build_catalog_payload(gate_state=McpActivationState.INACTIVE_MISSING_CONFIG)
    uris = {item.uri for item in payload.resources}
    assert "metagit://catalog" in uris
    assert "metagit://workspace/map" not in uris
    assert payload.dynamic_patterns == []
