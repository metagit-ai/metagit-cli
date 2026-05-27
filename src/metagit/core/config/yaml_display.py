#!/usr/bin/env python
"""
Human-readable YAML serialization for Metagit config display.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

_LITERAL_BLOCK_MIN_LENGTH = 88


def normalize_yaml_string(value: str) -> str:
    """Collapse messy wrapped descriptions into a single readable paragraph."""
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


def _represent_str(dumper: yaml.Dumper, value: str) -> yaml.nodes.ScalarNode:
    """Use literal block style for multiline or long strings; preserve Unicode."""
    normalized = normalize_yaml_string(value)
    if "\n" in normalized or len(normalized) >= _LITERAL_BLOCK_MIN_LENGTH:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str",
            normalized.rstrip("\n"),
            style="|",
        )
    return dumper.represent_scalar("tag:yaml.org,2002:str", normalized)


class _ReadableYamlDumper(yaml.SafeDumper):
    """Dumper tuned for terminal-friendly config output."""


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
