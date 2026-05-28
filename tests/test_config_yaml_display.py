#!/usr/bin/env python
"""Tests for config YAML display helpers."""

from metagit.core.config.yaml_display import (
    LITERAL_BLOCK_MIN_LENGTH,
    dump_config_dict,
    format_yaml_string,
    should_use_literal_block,
)


def test_should_use_literal_block_for_multiline_or_long_text() -> None:
    assert should_use_literal_block("line one\nline two") is True
    short = "x" * LITERAL_BLOCK_MIN_LENGTH
    assert should_use_literal_block(short) is False
    long = "x" * (LITERAL_BLOCK_MIN_LENGTH + 1)
    assert should_use_literal_block(long) is True


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


def test_dump_config_dict_uses_literal_block_for_long_single_line() -> None:
    long_text = "A" * (LITERAL_BLOCK_MIN_LENGTH + 5)
    rendered = dump_config_dict({"description": long_text})
    assert "description: |" in rendered
    assert long_text in rendered


def test_format_yaml_string_preserves_intentional_line_breaks() -> None:
    text = (
        "Metagit is situational awareness for developers and agents.\n"
        "It can make a sprawling multi-repo project feel more like a monorepo.\n"
    )
    formatted = format_yaml_string(text)
    assert formatted.count("\n") == 1
    assert "Metagit is situational awareness" in formatted


def test_dump_config_dict_indents_list_items() -> None:
    rendered = dump_config_dict(
        {
            "name": "demo",
            "documentation": [{"kind": "markdown", "path": "README.md"}],
            "workspace": {"projects": [{"name": "default", "repos": []}]},
        }
    )
    assert "\ndocumentation:\n  - kind: markdown" in rendered
    assert "\n    path: README.md" in rendered
    assert "\n  projects:\n    - name: default" in rendered
    assert "\n      repos:" in rendered


def test_dump_config_dict_uses_literal_block_for_messy_wrapped_description() -> None:
    messy = (
        "Repositories for managing AWS accounts, including account creation,\n"
        "management, and shared resources. Each repository\n\n"
        "corresponds to a specific AWS account\n"
    )
    rendered = dump_config_dict({"description": messy})
    assert "description: |" in rendered
    assert "Each repository" in rendered
    assert "corresponds to a specific AWS account" in rendered
