#!/usr/bin/env python
"""Resolve top-level CLI ``-c`` as AppConfig or Metagit manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, Sequence, Tuple, Union

import yaml

from metagit import DEFAULT_CONFIG
from metagit.core.appconfig import AppConfig, load_config
from metagit.core.appconfig.paths import local_appconfig_paths, user_appconfig_paths

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


def _as_config_path(path: Path | str) -> str:
    return str(Path(path).expanduser().resolve())


def _first_appconfig_file(candidates: Sequence[Path]) -> Optional[Path]:
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if detect_cli_config_file(key) == "appconfig":
            return Path(key)
    return None


def _missing_appconfig_candidates(requested: Path) -> list[Path]:
    candidates: list[Path] = []
    suffix = requested.suffix.lower()
    if suffix == ".yaml":
        candidates.append(requested.with_suffix(".yml"))
    elif suffix == ".yml":
        candidates.append(requested.with_suffix(".yaml"))
    candidates.extend(local_appconfig_paths(requested.parent))
    candidates.extend(user_appconfig_paths())
    return candidates


def resolve_cli_bootstrap(
    path: str,
) -> Tuple[Union[AppConfig, Exception], Optional[str], str]:
    """Load AppConfig for a CLI ``-c`` path.

    Returns ``(config_or_error, definition_path_or_None, appconfig_path)``.
    ``appconfig_path`` is always a YAML file (local, user, or bundled default),
    never ``workspace.path``.
    """
    kind = detect_cli_config_file(path)
    requested = Path(path).expanduser()
    if kind == "appconfig":
        appconfig_path = _as_config_path(requested)
        return load_config(appconfig_path), None, appconfig_path
    if kind == "manifest":
        found = _first_appconfig_file(
            [
                *local_appconfig_paths(requested.parent),
                *user_appconfig_paths(),
            ]
        )
        appconfig_path = _as_config_path(found) if found is not None else DEFAULT_CONFIG
        return load_config(appconfig_path), str(requested), appconfig_path
    if kind == "missing":
        found = _first_appconfig_file(_missing_appconfig_candidates(requested))
        appconfig_path = _as_config_path(found) if found is not None else DEFAULT_CONFIG
        return load_config(appconfig_path), None, appconfig_path
    return (
        ValueError(
            f"Path '{path}' is neither metagit.config.yaml (top-level 'config:') "
            "nor a .metagit.yml manifest (expected keys like name/kind/workspace)."
        ),
        None,
        DEFAULT_CONFIG,
    )
