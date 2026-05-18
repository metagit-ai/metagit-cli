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
            name = getattr(result, "repo_name", None) or getattr(
                result, "project_name", ""
            )
            click.echo(f"{entity} {operation}: {name}")
    if not bool(getattr(result, "ok", True)):
        raise SystemExit(1)
