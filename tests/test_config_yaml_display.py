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
