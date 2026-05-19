#!/usr/bin/env python
"""
Human-readable YAML serialization for Metagit config display.
"""

from __future__ import annotations

from typing import Any

import yaml


def _represent_str(dumper: yaml.Dumper, value: str) -> yaml.nodes.ScalarNode:
    """Use literal block style for multiline strings; preserve Unicode."""
    if "\n" in value:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str",
            value.rstrip("\n"),
            style="|",
        )
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


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
