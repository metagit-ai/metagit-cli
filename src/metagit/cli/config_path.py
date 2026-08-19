#!/usr/bin/env python
"""Resolve top-level CLI ``-c`` as AppConfig or Metagit manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, Tuple, Union

import yaml

from metagit import DEFAULT_CONFIG
from metagit.core.appconfig import AppConfig, load_config
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig

ConfigKind = Literal["appconfig", "manifest", "missing", "invalid"]
DEFAULT_MANIFEST = ".metagit.yml"


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
        # When given a manifest, try to find a local appconfig in the same directory
        manifest_path = Path(path).expanduser()
        manifest_dir = manifest_dir = manifest_path.parent
        local_appconfig = manifest_dir / "metagit.config.yaml"
        if local_appconfig.is_file():
            return load_config(str(local_appconfig)), str(manifest_path)
        cfg = load_config(DEFAULT_CONFIG)
        return cfg, str(manifest_path)
    return (
        ValueError(
            f"Path '{path}' is neither metagit.config.yaml (top-level 'config:') "
            "nor a .metagit.yml manifest (expected keys like name/kind/workspace)."
        ),
        None,
    )


def _ctx_obj(ctx: object) -> dict:
    raw = getattr(ctx, "obj", None)
    return raw if isinstance(raw, dict) else {}


def resolve_cli_manifest_path(
    explicit: Optional[str],
    ctx: object,
    *,
    default: str = DEFAULT_MANIFEST,
    force: bool = False,
) -> str:
    """Resolve a workspace manifest path from leaf/group flags or root ``-c``."""
    if force and explicit:
        return str(Path(explicit).expanduser())
    raw = explicit
    definition_from_ctx = _ctx_obj(ctx).get("definition_path")
    if isinstance(definition_from_ctx, str) and definition_from_ctx and (raw is None or raw == default):
        raw = definition_from_ctx
    if raw is None:
        raw = default
    return str(Path(raw).expanduser())


def resolve_cli_project(ctx: object, explicit: Optional[str] = None) -> Optional[str]:
    """Leaf/group ``--project`` wins, then root ``-p``."""
    if explicit:
        return explicit
    obj = _ctx_obj(ctx)
    command_project = obj.get("command_project")
    if isinstance(command_project, str) and command_project:
        return command_project
    target = obj.get("target_project")
    return target if isinstance(target, str) and target else None


def resolve_cli_repo(ctx: object, explicit: Optional[str] = None) -> Optional[str]:
    """Leaf ``--repo`` wins, then root ``--repo``."""
    if explicit:
        return explicit
    target = _ctx_obj(ctx).get("target_repo")
    return target if isinstance(target, str) and target else None


def bind_cli_manifest(
    ctx: object,
    explicit: Optional[str],
    *,
    force: bool = False,
) -> Union[MetagitConfig, Exception]:
    """Load ``.metagit.yml`` into ``ctx.obj`` (``config_path`` + ``local_config``)."""
    path = resolve_cli_manifest_path(explicit, ctx, force=force)
    loaded = MetagitConfigManager(path).load_config()
    if isinstance(loaded, Exception):
        return loaded
    obj = getattr(ctx, "obj", None)
    if isinstance(obj, dict):
        obj["config_path"] = path
        obj["local_config"] = loaded
    return loaded
