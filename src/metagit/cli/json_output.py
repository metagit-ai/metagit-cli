#!/usr/bin/env python
"""
Shared JSON output helpers for agentic CLI use.
"""

from __future__ import annotations

import json
from typing import Any

import click
from pydantic import BaseModel


def emit_json(payload: BaseModel | dict[str, Any]) -> None:
    """Print a JSON document to stdout."""
    if isinstance(payload, BaseModel):
        data: dict[str, Any] = payload.model_dump(mode="json")
    else:
        data = payload
    if isinstance(data, dict) and "schema_version" not in data:
        data = {"schema_version": "1.0", **data}
    click.echo(json.dumps(data, indent=2, default=str))


def exit_on_catalog_mutation(
    result: BaseModel,
    *,
    as_json: bool,
) -> None:
    """Emit mutation result and exit non-zero when ok is false."""
    if as_json:
        emit_json(result)
    else:
        ok = bool(getattr(result, "ok", True))
        error = getattr(result, "error", None)
        if not ok and error is not None:
            click.echo(f"Error ({error.kind}): {error.message}", err=True)
        elif ok:
            entity = getattr(result, "entity", "entity")
            operation = getattr(result, "operation", "updated")
            name = getattr(result, "repo_name", None) or getattr(result, "project_name", "")
            if operation == "noop":
                click.echo(f"{entity} unchanged (ensure): {name}")
            else:
                click.echo(f"{entity} {operation}: {name}")
    if not bool(getattr(result, "ok", True)):
        raise SystemExit(1)


def exit_on_layout_mutation(
    result: BaseModel,
    *,
    as_json: bool,
) -> None:
    """Emit layout mutation result; show plan summary on dry-run."""
    if as_json:
        emit_json(result)
    else:
        ok = bool(getattr(result, "ok", True))
        error = getattr(result, "error", None)
        data = getattr(result, "data", None) or {}
        if not ok and error is not None:
            click.echo(f"Error ({error.kind}): {error.message}", err=True)
        elif ok:
            operation = getattr(result, "operation", "updated")
            entity = getattr(result, "entity", "entity")
            name = getattr(result, "repo_name", None) or getattr(result, "project_name", "")
            if data.get("dry_run"):
                click.echo(f"dry-run {entity} {operation}: {name}")
                for step in data.get("disk_steps", []):
                    click.echo(f"  {step.get('action')}: {step.get('source')} -> {step.get('target')}")
            else:
                click.echo(f"{entity} {operation}: {name}")
                for warning in data.get("warnings", []):
                    click.echo(f"  warning: {warning}")
    if not bool(getattr(result, "ok", True)):
        raise SystemExit(1)
