#!/usr/bin/env python
"""
Human-readable YAML serialization for Metagit config display.
"""

from __future__ import annotations

import re
import textwrap
from typing import Any

import yaml

DEFAULT_WRAP_WIDTH = 88
LITERAL_BLOCK_MIN_LENGTH = DEFAULT_WRAP_WIDTH


def _looks_like_url(value: str) -> bool:
    trimmed = value.strip().lower()
    return trimmed.startswith("http://") or trimmed.startswith("https://")


def should_use_literal_block(value: str, *, wrap_width: int = DEFAULT_WRAP_WIDTH) -> bool:
    """Return True when a string should use YAML literal block (``|``) style."""
    if not value:
        return False
    if "\n" in value:
        return True
    stripped = value.strip()
    if _looks_like_url(stripped):
        return False
    return len(stripped) > wrap_width


def wrap_long_string(value: str, *, wrap_width: int = DEFAULT_WRAP_WIDTH) -> str:
    """Insert newlines at word boundaries for long single-line prose."""
    if not value or "\n" in value:
        return value
    stripped = value.strip()
    if len(stripped) <= wrap_width or _looks_like_url(stripped):
        return stripped
    return textwrap.fill(
        stripped,
        width=wrap_width,
        break_long_words=False,
        break_on_hyphens=False,
    )


def prepare_literal_block_string(
    value: str,
    *,
    wrap_width: int = DEFAULT_WRAP_WIDTH,
) -> str:
    """Normalize string content for YAML literal block output."""
    if not value:
        return value
    if "\n" not in value:
        return wrap_long_string(value, wrap_width=wrap_width)
    lines = [line.rstrip() for line in value.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= wrap_width:
            wrapped.append(line)
            continue
        wrapped.extend(
            textwrap.wrap(
                line,
                width=wrap_width,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return "\n".join(wrapped)


def normalize_yaml_string(value: str) -> str:
    """Collapse messy wrapped descriptions for inline YAML scalars."""
    if not value:
        return value
    stripped = value.strip()
    if "\n" not in stripped:
        return stripped
    if stripped.startswith(("- ", "* ", "#")) or "\n- " in stripped:
        return stripped.rstrip()
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if len(lines) <= 2 and all(len(line) < 72 for line in lines):
        return "\n".join(lines)
    return re.sub(r"\s+", " ", " ".join(lines))


def format_yaml_string(
    value: str,
    *,
    wrap_width: int = DEFAULT_WRAP_WIDTH,
) -> str:
    """Prepare a string for YAML output (block or inline)."""
    if should_use_literal_block(value, wrap_width=wrap_width):
        return prepare_literal_block_string(value, wrap_width=wrap_width)
    return normalize_yaml_string(value)


def _represent_str(dumper: yaml.Dumper, value: str) -> yaml.nodes.ScalarNode:
    """Use literal block style for multiline or long strings; preserve Unicode."""
    if should_use_literal_block(value):
        block = prepare_literal_block_string(value)
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str",
            block.rstrip("\n"),
            style="|",
        )
    normalized = normalize_yaml_string(value)
    return dumper.represent_scalar("tag:yaml.org,2002:str", normalized)


class _ReadableYamlDumper(yaml.SafeDumper):
    """Dumper tuned for terminal-friendly config output."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> Any:
        _ = indentless
        return super().increase_indent(flow, False)


_ReadableYamlDumper.add_representer(str, _represent_str)


def dump_config_dict(payload: dict[str, Any]) -> str:
    """
    Serialize a config dict for `metagit config show --normalized`.

    Multiline fields use `|` blocks; Unicode is not escaped.
    """
    return yaml.dump(
        payload,
        Dumper=_ReadableYamlDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        indent=2,
    )
