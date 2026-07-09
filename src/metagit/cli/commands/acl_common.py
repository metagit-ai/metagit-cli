#!/usr/bin/env python
"""Shared helpers for ACL CLI command groups."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import click

from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.root_resolver import (
    resolve_definition_root,
    resolve_session_root,
    resolve_sync_root,
)


def emit_json(payload: Any) -> None:
    if hasattr(payload, "model_dump"):
        click.echo(json.dumps(payload.model_dump(mode="json"), indent=2))
    elif isinstance(payload, Exception):
        click.echo(json.dumps({"ok": False, "error": str(payload)}, indent=2))
    else:
        click.echo(json.dumps(payload, indent=2))


def raise_if_error(result: Any) -> Any:
    if isinstance(result, Exception):
        raise click.ClickException(str(result))
    return result


def resolve_acl_roots(
    ctx: click.Context,
    definition_path: str,
) -> tuple[str, str, str]:
    """Return (session_root, sync_root, definition_path)."""
    path = Path(definition_path).expanduser()
    if path.name in {".metagit.yml", "metagit.yml"} and not path.is_file():
        parent = path.parent
        definition_root = str(Path.cwd().resolve()) if str(parent) in {"", "."} else str(parent.resolve())
    else:
        definition_root = resolve_definition_root(definition_path)
    session_root = resolve_session_root(definition_root)
    sync_root = session_root

    manager = MetagitConfigManager(config_path=definition_path)
    config = manager.load_config()
    if isinstance(config, MetagitConfig):
        config_path: Optional[str] = None
        if ctx.obj:
            config_path = ctx.obj.get("config_path")
        if config_path:
            appconfig = load_appconfig(config_path)
            if not isinstance(appconfig, Exception) and appconfig.workspace and appconfig.workspace.path:
                sync_root = resolve_sync_root(definition_root, appconfig.workspace.path)

    return session_root, sync_root, definition_path


__all__ = ["emit_json", "raise_if_error", "resolve_acl_roots"]
