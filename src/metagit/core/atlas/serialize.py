#!/usr/bin/env python
"""Deterministic YAML helpers for Atlas artifacts."""

from __future__ import annotations

from typing import Any

import yaml


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    )


def load_yaml(text: str) -> Any:
    return yaml.safe_load(text)


__all__ = [
    "dump_yaml",
    "load_yaml",
]
