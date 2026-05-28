#!/usr/bin/env python
"""Tests for documentation list compaction during config formatting."""

from __future__ import annotations

from metagit.core.config.documentation_models import (
    DocumentationSource,
    compact_documentation_entry,
    compact_documentation_list,
)
from metagit.core.config.format_service import ConfigFormatService
from metagit.core.config.models import MetagitConfig


def test_compact_documentation_entry_uses_string_shorthand() -> None:
    markdown = DocumentationSource(kind="markdown", path="README.md")
    web = DocumentationSource(
        kind="web",
        url="https://metagit-ai.github.io/metagit-cli/",
    )
    assert compact_documentation_entry(markdown) == "README.md"
    assert (
        compact_documentation_entry(web)
        == "https://metagit-ai.github.io/metagit-cli/"
    )


def test_compact_documentation_entry_keeps_rich_objects() -> None:
    confluence = DocumentationSource(
        kind="confluence",
        url="https://confluence.example.com/display/METAGIT/Docs",
        tags={"playbook": "true"},
    )
    markdown_with_metadata = DocumentationSource(
        kind="markdown",
        path="CHANGELOG.md",
        metadata={"ingest": "knowledge-graph"},
    )
    assert compact_documentation_entry(confluence) == {
        "kind": "confluence",
        "url": "https://confluence.example.com/display/METAGIT/Docs",
        "tags": {"playbook": "true"},
    }
    assert compact_documentation_entry(markdown_with_metadata) == {
        "kind": "markdown",
        "path": "CHANGELOG.md",
        "metadata": {"ingest": "knowledge-graph"},
    }


def test_compact_documentation_list_deduplicates_and_prefers_shorthand() -> None:
    entries = [
        DocumentationSource(kind="markdown", path="README.md"),
        DocumentationSource(kind="markdown", path="README.md"),
        DocumentationSource(
            kind="web",
            url="https://metagit-ai.github.io/metagit-cli/",
        ),
        DocumentationSource(
            kind="web",
            url="https://metagit-ai.github.io/metagit-cli/",
        ),
        DocumentationSource(
            kind="confluence",
            url="https://confluence.example.com/display/METAGIT/Docs",
            tags={"playbook": "true"},
        ),
    ]
    compacted = compact_documentation_list(entries)
    assert compacted == [
        "README.md",
        "https://metagit-ai.github.io/metagit-cli/",
        {
            "kind": "confluence",
            "url": "https://confluence.example.com/display/METAGIT/Docs",
            "tags": {"playbook": "true"},
        },
    ]


def test_compact_documentation_list_keeps_richer_duplicate() -> None:
    entries = [
        DocumentationSource(kind="markdown", path="CHANGELOG.md"),
        DocumentationSource(
            kind="markdown",
            path="CHANGELOG.md",
            metadata={"ingest": "knowledge-graph"},
        ),
    ]
    compacted = compact_documentation_list(entries)
    assert compacted == [
        {
            "kind": "markdown",
            "path": "CHANGELOG.md",
            "metadata": {"ingest": "knowledge-graph"},
        }
    ]


def test_render_metagit_formats_documentation_block() -> None:
    config = MetagitConfig(
        name="demo",
        documentation=[
            "README.md",
            {"kind": "markdown", "path": "README.md"},
            "https://metagit-ai.github.io/metagit-cli/",
            {
                "kind": "confluence",
                "url": "https://confluence.example.com/display/METAGIT/Docs",
                "tags": ["playbook"],
            },
        ],
        workspace={"projects": []},
    )
    rendered = ConfigFormatService().render_metagit(config)
    assert "\ndocumentation:\n  - README.md\n" in rendered
    assert "  - https://metagit-ai.github.io/metagit-cli/" in rendered
    assert "  - kind: confluence" in rendered
    assert rendered.count("README.md") == 1
