#!/usr/bin/env python
"""Resolve top-level CLI ``-c`` as AppConfig or Metagit manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, Tuple, Union

import yaml

from metagit import DEFAULT_CONFIG
from metagit.core.appconfig import AppConfig, load_config

ConfigKind = Literal["appconfig", "manifest", "missing", "invalid"]


def detect_cli_config_file(path: str) -> ConfigKind:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        return "missing"
    try:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except Exception:
        return "invalid"
    if not isinstance(data, dict):
        return "invalid"
    if "config" in data and isinstance(data["config"], dict):
        return "appconfig"
    if any(key in data for key in ("name", "kind", "workspace")):
        return "manifest"
    return "invalid"


def resolve_cli_bootstrap(
    path: str,
) -> Tuple[Union[AppConfig, Exception], Optional[str]]:
    kind = detect_cli_config_file(path)
    if kind == "missing":
        cfg = load_config(DEFAULT_CONFIG)
        return cfg, None
    if kind == "appconfig":
        return load_config(path), None
    if kind == "manifest":
        cfg = load_config(DEFAULT_CONFIG)
        return cfg, str(Path(path).expanduser())
    return (
        ValueError(
            f"Path '{path}' is neither metagit.config.yaml (top-level 'config:') "
            "nor a .metagit.yml manifest (expected keys like name/kind/workspace)."
        ),
        None,
    )
