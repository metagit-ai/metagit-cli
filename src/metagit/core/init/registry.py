#!/usr/bin/env python
"""Load bundled init templates from package data."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from metagit import DATA_PATH
from metagit.core.init.models import InitTemplateManifest
from metagit.core.utils.yaml_class import yaml


class InitTemplateRegistry:
    """Discover and load init templates shipped under data/init-templates."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = root or Path(DATA_PATH) / "init-templates"

    @property
    def root(self) -> Path:
        return self._root

    def list_templates(self) -> list[InitTemplateManifest]:
        """Return all valid template manifests sorted by id."""
        manifests: list[InitTemplateManifest] = []
        if not self._root.is_dir():
            return manifests
        for entry in sorted(self._root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            manifest = self.load_manifest(entry.name)
            if manifest is not None:
                manifests.append(manifest)
        return manifests

    def load_manifest(self, template_id: str) -> Optional[InitTemplateManifest]:
        """Load template.yaml for a template id."""
        manifest_path = self._safe_template_path(template_id) / "template.yaml"
        if not manifest_path.is_file():
            return None
        with manifest_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        if not isinstance(raw, dict):
            return None
        return InitTemplateManifest.model_validate(raw)

    def template_dir(self, template_id: str) -> Path:
        """Return the directory containing template sources."""
        return self._safe_template_path(template_id)

    def _safe_template_path(self, template_id: str) -> Path:
        if not template_id or ".." in template_id or "/" in template_id:
            raise ValueError(f"invalid template id: {template_id!r}")
        return self._root / template_id
