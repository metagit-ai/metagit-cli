#!/usr/bin/env python
"""Tests for config YAML display helpers."""

from metagit.core.config.yaml_display import dump_config_dict


def test_dump_config_dict_uses_literal_block_for_multiline() -> None:
    rendered = dump_config_dict(
        {
            "name": "demo",
            "agent_instructions": "line one\nline two",
        }
    )
    assert "agent_instructions: |" in rendered
    assert "line one" in rendered
    assert "\\u2014" not in rendered
    rendered_unicode = dump_config_dict({"note": "status — ok"})
    assert "—" in rendered_unicode
    assert "\\u2014" not in rendered_unicode


def test_dump_config_dict_collapses_messy_wrapped_description() -> None:
    messy = (
        "Repositories for managing AWS accounts, including account creation,\n"
        "management, and shared resources. Each repository\n\n"
        "corresponds to a specific AWS account\n"
    )
    rendered = dump_config_dict({"description": messy})
    assert "description: |" in rendered
    assert "Each repository corresponds" in rendered.replace("\n", " ")
    assert "Each repository\n\n" not in rendered
