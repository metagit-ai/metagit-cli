#!/usr/bin/env python
"""Load bundled and overlay agent templates from package data."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from metagit import DATA_PATH
from metagit.core.agent.models import AgentTemplateManifest, AgentTemplateSource
from metagit.core.agent.overlay import (
    load_overlay_payload,
    merge_manifest_payloads,
    overlay_template_dir,
    resolve_committed_overlay_root,
    resolve_local_overlay_root,
    resolve_template_file,
    resolve_template_source,
)
from metagit.core.utils.yaml_class import yaml


class AgentTemplateRegistry:
    """Discover and load agent templates shipped under data/agent-templates."""

    def __init__(
        self,
        *,
        bundled_root: Optional[Path] = None,
        manifest_root: Optional[Path] = None,
    ) -> None:
        self._bundled_root = bundled_root or Path(DATA_PATH) / "agent-templates"
        self._manifest_root = Path(manifest_root).resolve() if manifest_root is not None else None
        self._committed_overlay_root = resolve_committed_overlay_root(self._manifest_root)
        self._local_overlay_root = resolve_local_overlay_root(self._manifest_root)

    @property
    def bundled_root(self) -> Path:
        return self._bundled_root

    @property
    def manifest_root(self) -> Path | None:
        return self._manifest_root

    @property
    def committed_overlay_root(self) -> Path | None:
        return self._committed_overlay_root

    @property
    def local_overlay_root(self) -> Path | None:
        return self._local_overlay_root

    @property
    def overlay_root(self) -> Path | None:
        """First existing overlay root (committed, then local)."""
        return self._committed_overlay_root or self._local_overlay_root

    @property
    def shared_root(self) -> Path:
        return self._bundled_root / "_shared"

    def list_template_ids(self) -> list[str]:
        """Return all template ids from bundled and overlay sources."""
        ids: set[str] = set()
        ids.update(self._discover_ids(self._bundled_root))
        for overlay_root in (
            self._committed_overlay_root,
            self._local_overlay_root,
        ):
            if overlay_root is not None:
                ids.update(self._discover_ids(overlay_root))
        return sorted(ids)

    def list_templates(self) -> list[AgentTemplateManifest]:
        """Return all valid template manifests sorted by id."""
        manifests: list[AgentTemplateManifest] = []
        for template_id in self.list_template_ids():
            manifest = self.load_manifest(template_id)
            if manifest is not None:
                manifests.append(manifest)
        return manifests

    def load_manifest(self, template_id: str) -> Optional[AgentTemplateManifest]:
        """Load merged template.yaml for a template id."""
        return self._validate_merged_payload(
            self._merged_manifest_payload(template_id),
        )

    def load_bundled_manifest(self, template_id: str) -> Optional[AgentTemplateManifest]:
        """Load bundled-only manifest."""
        return self._load_bundled_manifest(template_id)

    def load_overlay_manifest(self, template_id: str) -> Optional[AgentTemplateManifest]:
        """Load merged committed + local overlay manifests on top of bundled."""
        return self._validate_merged_payload(
            self._merged_manifest_payload(template_id, include_bundled=False),
        )

    def resolve_source(self, template_id: str) -> AgentTemplateSource:
        """Return whether a template resolves from bundled, overlay, or both."""
        bundled_exists = self._bundled_template_dir(template_id).is_dir()
        overlay_exists = self._has_any_overlay(template_id)
        return resolve_template_source(
            bundled_exists=bundled_exists,
            overlay_exists=overlay_exists,
        )

    def overlay_path_for(self, template_id: str) -> Path | None:
        """Return the primary overlay directory (committed, else local)."""
        for overlay_root in (
            self._committed_overlay_root,
            self._local_overlay_root,
        ):
            if overlay_root is None:
                continue
            directory = overlay_template_dir(overlay_root, template_id)
            if directory.is_dir():
                return directory
        return None

    def template_dir(self, template_id: str) -> Path:
        """Return bundled template directory (legacy callers)."""
        return self._bundled_template_dir(template_id)

    def resolve_source_file(self, template_id: str, filename: str) -> Path | None:
        """Resolve a template source with local > committed > bundled precedence."""
        bundled_dir = (
            self._bundled_template_dir(template_id) if self._bundled_template_dir(template_id).is_dir() else None
        )
        overlay_dirs = self._overlay_dirs_for_template(template_id)
        return resolve_template_file(
            template_id=template_id,
            filename=filename,
            bundled_dir=bundled_dir,
            overlay_dirs=overlay_dirs,
            shared_dir=self.shared_root if self.shared_root.is_dir() else None,
        )

    def list_template_files(self, template_id: str) -> list[str]:
        """List known template file basenames for detail endpoints."""
        names: set[str] = set()
        for directory in (
            self._bundled_template_dir(template_id),
            self._overlay_dir_for_scope(self._local_overlay_root, template_id),
            self._overlay_dir_for_scope(self._committed_overlay_root, template_id),
        ):
            if directory is None or not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix != ".tpl" and path.name != "template.yaml":
                    continue
                if path.name == "template.yaml":
                    names.add("template.yaml")
                    continue
                relative = path.relative_to(directory)
                names.add(str(relative))
        return sorted(names)

    def _overlay_dirs_for_template(self, template_id: str) -> list[Path]:
        """Return overlay directories highest-precedence first."""
        directories: list[Path] = []
        for overlay_root in (
            self._local_overlay_root,
            self._committed_overlay_root,
        ):
            directory = self._overlay_dir_for_scope(overlay_root, template_id)
            if directory is not None:
                directories.append(directory)
        return directories

    def _has_any_overlay(self, template_id: str) -> bool:
        return bool(self._overlay_dirs_for_template(template_id))

    def _overlay_dir_for_scope(
        self,
        overlay_root: Path | None,
        template_id: str,
    ) -> Path | None:
        if overlay_root is None:
            return None
        directory = overlay_template_dir(overlay_root, template_id)
        return directory if directory.is_dir() else None

    def _merged_manifest_payload(
        self,
        template_id: str,
        *,
        include_bundled: bool = True,
    ) -> dict[str, Any] | None:
        payloads: list[dict[str, Any] | None] = []
        if include_bundled:
            bundled = self._load_bundled_manifest(template_id)
            payloads.append(bundled.model_dump() if bundled is not None else None)
        payloads.append(self._load_scope_overlay_payload(self._committed_overlay_root, template_id))
        payloads.append(self._load_scope_overlay_payload(self._local_overlay_root, template_id))
        merged: dict[str, Any] | None = None
        for payload in payloads:
            merged = merge_manifest_payloads(merged, payload)
        return merged

    def _validate_merged_payload(
        self,
        payload: dict[str, Any] | None,
    ) -> Optional[AgentTemplateManifest]:
        if payload is None:
            return None
        return AgentTemplateManifest.model_validate(payload)

    def _load_scope_overlay_payload(
        self,
        overlay_root: Path | None,
        template_id: str,
    ) -> dict[str, Any] | None:
        if overlay_root is None:
            return None
        return load_overlay_payload(overlay_root, template_id)

    def _discover_ids(self, root: Path) -> set[str]:
        ids: set[str] = set()
        if not root.is_dir():
            return ids
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            if entry.name.startswith(".") or entry.name.startswith("_"):
                continue
            if (entry / "template.yaml").is_file():
                ids.add(entry.name)
        return ids

    def _load_bundled_manifest(self, template_id: str) -> Optional[AgentTemplateManifest]:
        manifest_path = self._bundled_template_dir(template_id) / "template.yaml"
        if not manifest_path.is_file():
            return None
        with manifest_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        if not isinstance(raw, dict):
            return None
        return AgentTemplateManifest.model_validate(raw)

    def _bundled_template_dir(self, template_id: str) -> Path:
        if not template_id or ".." in template_id or "/" in template_id:
            raise ValueError(f"invalid template id: {template_id!r}")
        return self._bundled_root / template_id
