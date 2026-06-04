#!/usr/bin/env python
"""Tests for documentation tag normalization."""

from __future__ import annotations

from metagit.core.config.documentation_models import (
    DocumentationSource,
    normalize_documentation_tags,
)


def test_normalize_documentation_tags_from_list() -> None:
    assert normalize_documentation_tags(["playbook", "tutorial"]) == [
        "playbook",
        "tutorial",
    ]


def test_normalize_documentation_tags_from_legacy_map() -> None:
    assert normalize_documentation_tags(
        {"playbook": "true", "tutorial": "true", "docker": "false"}
    ) == ["playbook", "tutorial"]


def test_normalize_documentation_tags_from_map_with_values() -> None:
    assert normalize_documentation_tags({"priority": "high"}) == ["priority=high"]


def test_documentation_source_emits_tag_list() -> None:
    entry = DocumentationSource(
        kind="web",
        url="https://example.com/docs",
        tags=["playbook", "tutorial"],
    )
    assert entry.tags == ["playbook", "tutorial"]
    assert entry.graph_node_payload()["tags"] == ["playbook", "tutorial"]
