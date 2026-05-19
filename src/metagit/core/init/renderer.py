#!/usr/bin/env python
"""Render init template files and validate Metagit manifests."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from metagit.core.config.models import MetagitConfig
from metagit.core.init.models import InitTemplateFileSpec, InitTemplateManifest
from metagit.core.utils.yaml_class import yaml

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def render_placeholders(content: str, context: dict[str, str]) -> str:
    """Replace ``{{ name }}`` placeholders (copier-style, no extra deps)."""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return context.get(key, "")

    return _PLACEHOLDER.sub(_replace, content)


def clean_manifest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove empty optional keys before validation."""
    cleaned = dict(payload)
    for key in ("url", "agent_instructions"):
        value = cleaned.get(key)
        if value is None or value == "":
            cleaned.pop(key, None)
    return cleaned


def validate_metagit_yaml(content: str) -> MetagitConfig:
    """Parse and validate rendered .metagit.yml content."""
    loaded = yaml.safe_load(content)
    if not isinstance(loaded, dict):
        raise ValueError("rendered manifest is not a YAML mapping")
    return MetagitConfig.model_validate(clean_manifest_payload(loaded))


class InitTemplateRenderer:
    """Render template files for a target directory."""

    def render_file(
        self,
        template_dir: Path,
        file_spec: InitTemplateFileSpec,
        context: dict[str, str],
    ) -> str:
        source = template_dir / file_spec.template
        if not source.is_file():
            raise FileNotFoundError(f"template file not found: {source}")
        raw = source.read_text(encoding="utf-8")
        return render_placeholders(raw, context)

    def render_manifest(
        self,
        template_dir: Path,
        manifest: InitTemplateManifest,
        context: dict[str, str],
    ) -> list[tuple[InitTemplateFileSpec, str]]:
        """Render all files declared in the manifest."""
        rendered: list[tuple[InitTemplateFileSpec, str]] = []
        for file_spec in manifest.files:
            content = self.render_file(template_dir, file_spec, context)
            if file_spec.optional and not content.strip():
                continue
            if file_spec.output == ".metagit.yml":
                validate_metagit_yaml(content)
            rendered.append((file_spec, content))
        return rendered
