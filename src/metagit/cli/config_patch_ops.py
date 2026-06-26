#!/usr/bin/env python
"""Shared helpers for config patch/preview CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from metagit.core.config.patch_service import PatchResult, PreviewResult, TreeResult
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.web.models import ConfigOperation, ConfigOpKind, ConfigPatchRequest


def parse_cli_value(raw: str) -> Any:
    """Parse --value as JSON when possible, otherwise return the raw string."""
    stripped = raw.strip()
    if not stripped:
        return ""
    if stripped[0] in '{["':
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON value: {exc}") from exc
    if stripped.lower() in {"true", "false"}:
        return stripped.lower() == "true"
    if stripped.isdigit():
        return int(stripped)
    try:
        if "." in stripped:
            return float(stripped)
    except ValueError:
        pass
    return raw


def load_operations_file(path: str) -> list[ConfigOperation]:
    """Load operations from a JSON file (ConfigPatchRequest or operations array)."""
    file_path = Path(path)
    if not file_path.is_file():
        raise click.ClickException(f"Operations file not found: {path}")
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in {path}: {exc}") from exc
    if isinstance(payload, list):
        return [ConfigOperation.model_validate(item) for item in payload]
    if isinstance(payload, dict):
        if "operations" in payload:
            request = ConfigPatchRequest.model_validate(payload)
            return list(request.operations)
        raise click.ClickException(f"{path} must be a JSON array of operations or an object with 'operations'")
    raise click.ClickException(f"{path} must contain a JSON object or array")


def resolve_operations(
    *,
    operations_file: str | None,
    op: str | None,
    path: str | None,
    value: str | None,
) -> list[ConfigOperation]:
    """Resolve operations from --file or a single --op/--path/--value triplet."""
    if operations_file:
        if op or path or value is not None:
            raise click.ClickException("Use either --file or --op/--path/--value, not both")
        return load_operations_file(operations_file)
    if not op or not path:
        raise click.ClickException("Provide --file <path.json> or --op <kind> --path <field.path>")
    try:
        op_kind = ConfigOpKind(op.lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ConfigOpKind)
        raise click.ClickException(f"Invalid --op '{op}'; must be one of: {allowed}") from exc
    parsed_value = parse_cli_value(value) if value is not None else None
    if op_kind == ConfigOpKind.SET and parsed_value is None:
        raise click.ClickException("--op set requires --value")
    return [
        ConfigOperation(op=op_kind, path=path, value=parsed_value),
    ]


def emit_patch_result(
    result: PatchResult,
    *,
    as_json: bool,
    logger: UnifiedLogger,
) -> None:
    """Print patch outcome and abort on failure when not saving with errors."""
    if as_json:
        click.echo(
            json.dumps(
                result.model_dump(mode="json", exclude_none=True),
                indent=2,
            )
        )
        if not result.ok:
            raise SystemExit(1)
        return
    if result.validation_errors:
        logger.error("Validation failed after applying operations:")
        for item in result.validation_errors:
            logger.error(f"  {item.get('path', '')}: {item.get('message', '')}")
    if result.saved:
        logger.success(f"Saved {result.config_path}")
    elif result.ok:
        logger.info("Operations applied (dry run; use --save to write)")
    if not result.ok:
        raise SystemExit(1)


def emit_preview_result(
    result: PreviewResult,
    *,
    as_json: bool,
    logger: UnifiedLogger,
    output_path: str | None,
) -> None:
    """Print or write YAML preview."""
    if output_path:
        Path(output_path).write_text(result.yaml, encoding="utf-8")
        logger.success(f"Preview written to {output_path}")
    if as_json:
        payload = result.model_dump(mode="json", exclude_none=True)
        if output_path:
            payload["written_to"] = output_path
        click.echo(json.dumps(payload, indent=2))
    else:
        if result.validation_errors:
            logger.warning("Preview has validation errors:")
            for item in result.validation_errors:
                logger.warning(f"  {item.get('path', '')}: {item.get('message', '')}")
        click.echo(result.yaml, nl=result.yaml.endswith("\n"))
    if not result.ok:
        raise SystemExit(1)


def emit_tree_result(
    result: TreeResult,
    *,
    as_json: bool,
) -> None:
    """Print schema tree."""
    if as_json:
        click.echo(json.dumps(result.model_dump(mode="json"), indent=2))
        return
    click.echo(f"config: {result.config_path}")
    _print_tree_node(result.tree, indent=0)


def _print_tree_node(node: Any, *, indent: int) -> None:
    prefix = "  " * indent
    label = node.type_label or node.type
    enabled = "on" if node.enabled else "off"
    path = node.path or "(root)"
    if node.type not in {"object", "array"}:
        value = node.value
        click.echo(f"{prefix}{path} [{label}, {enabled}] = {value!r}")
    else:
        extra = ""
        if node.item_count is not None:
            extra = f", items={node.item_count}"
        if node.can_append:
            extra = f"{extra}, appendable"
        click.echo(f"{prefix}{path} [{label}, {enabled}{extra}]")
    for child in node.children:
        _print_tree_node(child, indent=indent + 1)
