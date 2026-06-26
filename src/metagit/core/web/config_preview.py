#!/usr/bin/env python
"""Render YAML previews for metagit web config editor."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from metagit.core.appconfig.agent_mode import resolve_agent_mode
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.config.yaml_display import dump_config_dict
from metagit.core.web.schema_tree import SchemaTreeService

PreviewStyle = Literal["normalized", "minimal", "disk"]

_SENSITIVE_KEYS = SchemaTreeService.SENSITIVE_KEYS


def read_disk_text(path: str) -> str:
    """Return on-disk file contents or empty string when missing."""
    file_path = Path(path)
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def redact_secrets(payload: Any) -> Any:
    """Return a copy of nested dict/list data with sensitive string values masked."""
    if isinstance(payload, dict):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            if key in _SENSITIVE_KEYS or key.endswith("_token"):
                if isinstance(value, str) and value:
                    suffix = value[-4:] if len(value) > 4 else ""
                    redacted[key] = f"***{suffix}" if suffix else "***"
                else:
                    redacted[key] = value
            else:
                redacted[key] = redact_secrets(value)
        return redacted
    if isinstance(payload, list):
        return [redact_secrets(item) for item in payload]
    return payload


def render_metagit_yaml(
    config: MetagitConfig,
    *,
    style: PreviewStyle,
) -> str:
    """Serialize a metagit manifest for preview."""
    if style == "minimal":
        payload = config.model_dump(exclude_none=True, exclude_defaults=True, mode="json")
    else:
        payload = config.model_dump(exclude_none=True, mode="json")
    return dump_config_dict(payload)


def render_appconfig_yaml(
    config: AppConfig,
    *,
    config_path: str,
    style: PreviewStyle,
    mask_secrets: bool,
) -> str:
    """Serialize application config for preview."""
    if style == "minimal":
        config_body = config.model_dump(
            exclude_none=True,
            exclude_defaults=True,
            mode="json",
        )
        payload: dict[str, Any] = {"config": config_body}
    else:
        config_body = config.model_dump(mode="json")
        payload = {
            "config_path": config_path,
            "agent_mode": resolve_agent_mode(config),
            "config": config_body,
        }
    if mask_secrets:
        payload = redact_secrets(payload)
    if style == "minimal":
        return dump_config_dict({"config": payload["config"]})
    return dump_config_dict(payload)
