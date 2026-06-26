#!/usr/bin/env python
"""Workspace overlay resolution for agent templates."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from metagit.core.agent.models import (
    AgentOverlayInitMode,
    AgentOverlayInitResult,
    AgentOverlayScope,
    AgentTemplateManifest,
    AgentTemplateSource,
)
from metagit.core.utils.yaml_class import yaml

COMMITTED_OVERLAY_RELATIVE = Path(".metagit-agents")
LOCAL_OVERLAY_RELATIVE = Path(".metagit") / ".agent-templates"
# Backward-compatible alias for docs that referenced the old default path.
OVERLAY_RELATIVE = LOCAL_OVERLAY_RELATIVE

_MINIMAL_OVERLAY_FILES = frozenset({"template.yaml", "body.md.tpl"})
_OVERLAY_MANIFEST_HEADER = """# Workspace overlay for {template_id}.
# Edit files under this directory; omitted manifest fields inherit from the bundled template.
# Template files here override bundled sources with the same name.

"""
_MINIMAL_MANIFEST_STUB = """# Workspace overlay — uncomment and edit fields you want to override.
schema_version: "1.0"
id: {template_id}
# label: Custom label
# description: |
#   Custom description for this workspace.
"""


def overlay_relative_for_scope(scope: AgentOverlayScope) -> Path:
    """Return the path segment(s) for one overlay scope."""
    return LOCAL_OVERLAY_RELATIVE if scope == AgentOverlayScope.LOCAL else COMMITTED_OVERLAY_RELATIVE


def overlay_path_for_template(
    manifest_root: Path,
    template_id: str,
    *,
    scope: AgentOverlayScope = AgentOverlayScope.COMMITTED,
) -> Path:
    """Return overlay directory for one template under a manifest root."""
    return (manifest_root / overlay_relative_for_scope(scope) / template_id).resolve()


def resolve_committed_overlay_root(manifest_root: Path | None) -> Path | None:
    """Return `.metagit-agents` when present under manifest root."""
    if manifest_root is None:
        return None
    candidate = (manifest_root / COMMITTED_OVERLAY_RELATIVE).resolve()
    return candidate if candidate.is_dir() else None


def resolve_local_overlay_root(manifest_root: Path | None) -> Path | None:
    """Return `.metagit/.agent-templates` when present under manifest root."""
    if manifest_root is None:
        return None
    candidate = (manifest_root / LOCAL_OVERLAY_RELATIVE).resolve()
    return candidate if candidate.is_dir() else None


def resolve_overlay_root(manifest_root: Path | None) -> Path | None:
    """Return the first existing overlay root (committed, then local)."""
    committed = resolve_committed_overlay_root(manifest_root)
    if committed is not None:
        return committed
    return resolve_local_overlay_root(manifest_root)


def ensure_overlay_root(
    manifest_root: Path,
    *,
    scope: AgentOverlayScope = AgentOverlayScope.COMMITTED,
) -> Path:
    """Create the overlay root directory for one scope when missing."""
    overlay_root = (manifest_root / overlay_relative_for_scope(scope)).resolve()
    overlay_root.mkdir(parents=True, exist_ok=True)
    return overlay_root


def overlay_has_files(
    manifest_root: Path,
    template_id: str,
    *,
    scope: AgentOverlayScope,
) -> bool:
    """Return True when an overlay directory already contains files."""
    directory = overlay_path_for_template(manifest_root, template_id, scope=scope)
    if not directory.is_dir():
        return False
    return any(directory.rglob("*"))


def _relative_overlay_files(
    bundled_dir: Path,
    *,
    mode: AgentOverlayInitMode,
) -> list[Path]:
    if not bundled_dir.is_dir():
        return []
    if mode == AgentOverlayInitMode.FULL:
        return sorted(path.relative_to(bundled_dir) for path in bundled_dir.rglob("*") if path.is_file())
    return sorted(Path(name) for name in _MINIMAL_OVERLAY_FILES if (bundled_dir / name).is_file())


def _prepare_overlay_manifest(
    content: str,
    *,
    template_id: str,
    mode: AgentOverlayInitMode,
    scope: AgentOverlayScope,
) -> str:
    if mode == AgentOverlayInitMode.MINIMAL:
        return _MINIMAL_MANIFEST_STUB.format(template_id=template_id)
    scope_note = (
        "Commit this directory to git for team-wide agent definitions."
        if scope == AgentOverlayScope.COMMITTED
        else "Personal override only; this path is usually gitignored with `.metagit/`."
    )
    header = _OVERLAY_MANIFEST_HEADER.format(template_id=template_id)
    header += f"# Scope: {scope.value} — {scope_note}\n\n"
    stripped = content.lstrip("\ufeff")
    if stripped.startswith("# Workspace overlay for"):
        return stripped
    return header + stripped


def init_overlay_from_bundled(
    *,
    template_id: str,
    manifest_root: Path,
    bundled_dir: Path,
    scope: AgentOverlayScope = AgentOverlayScope.COMMITTED,
    mode: AgentOverlayInitMode = AgentOverlayInitMode.FULL,
    force: bool = False,
    dry_run: bool = False,
) -> AgentOverlayInitResult:
    """Copy bundled template sources into a workspace overlay directory."""
    destination = overlay_path_for_template(manifest_root, template_id, scope=scope)
    if overlay_has_files(manifest_root, template_id, scope=scope) and not force:
        raise FileExistsError(f"overlay already exists: {destination} (use force=True to replace files)")
    relative_files = _relative_overlay_files(bundled_dir, mode=mode)
    if not relative_files:
        raise ValueError(f"no bundled template files to copy for {template_id!r}")

    written: list[str] = []
    if not dry_run:
        ensure_overlay_root(manifest_root, scope=scope)
        if force and destination.is_dir():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)

    for relative in relative_files:
        source = bundled_dir / relative
        target = destination / relative
        content = source.read_text(encoding="utf-8")
        if relative.name == "template.yaml":
            content = _prepare_overlay_manifest(
                content,
                template_id=template_id,
                mode=mode,
                scope=scope,
            )
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        written.append(str(target))

    readme_name = "OVERLAY.md"
    readme_path = destination / readme_name
    if scope == AgentOverlayScope.COMMITTED:
        readme_content = (
            f"# Overlay: {template_id}\n\n"
            "Team-committed agent template customizations for this workspace.\n\n"
            "- **Commit** this `.metagit-agents/` tree to git so the team shares it.\n"
            "- `template.yaml` fields deep-merge with the bundle; lists replace bundled lists.\n"
            "- `.tpl` files here override bundled files with the same name.\n"
            "- Run `metagit agent validate --root <manifest-root>` after edits.\n"
        )
    else:
        readme_content = (
            f"# Overlay: {template_id}\n\n"
            "Personal/local overlay under gitignored `.metagit/`.\n\n"
            "- Use for machine-specific tweaks; prefer `.metagit-agents/` for team defaults.\n"
            "- Local overlays take precedence over committed overlays and the bundle.\n"
            "- Run `metagit agent validate --root <manifest-root>` after edits.\n"
        )
    if not dry_run:
        readme_path.write_text(readme_content, encoding="utf-8")
    written.append(str(readme_path))

    return AgentOverlayInitResult(
        template_id=template_id,
        overlay_path=str(destination),
        scope=scope,
        mode=mode,
        paths=written,
        dry_run=dry_run,
    )


def primary_overlay_edit_path(result: AgentOverlayInitResult) -> str | None:
    """Return the best file to open after scaffolding an overlay."""
    for candidate in ("template.yaml", "body.md.tpl"):
        for path_value in result.paths:
            if os.path.basename(path_value) == candidate:
                return path_value
    return result.paths[0] if result.paths else None


def overlay_template_dir(overlay_root: Path, template_id: str) -> Path:
    """Return overlay directory for one template id."""
    if not template_id or ".." in template_id or "/" in template_id:
        raise ValueError(f"invalid template id: {template_id!r}")
    return overlay_root / template_id


def load_overlay_payload(
    overlay_root: Path,
    template_id: str,
) -> dict[str, Any] | None:
    """Load overlay template.yaml as a partial payload (not fully validated)."""
    manifest_path = overlay_template_dir(overlay_root, template_id) / "template.yaml"
    if not manifest_path.is_file():
        return None
    with manifest_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return None
    payload = dict(raw)
    if "id" not in payload:
        payload["id"] = template_id
    return payload


def load_overlay_manifest(
    overlay_root: Path,
    template_id: str,
) -> AgentTemplateManifest | None:
    """Load overlay template.yaml when present."""
    payload = load_overlay_payload(overlay_root, template_id)
    if payload is None:
        return None
    return AgentTemplateManifest.model_validate(payload)


def _deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(existing, value)
        else:
            merged[key] = value
    return merged


def merge_manifest_payloads(
    bundled: dict[str, Any] | None,
    overlay: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Deep-merge manifest dicts; overlay lists replace bundled lists."""
    if bundled is None and overlay is None:
        return None
    if bundled is None:
        return dict(overlay or {})
    if overlay is None:
        return dict(bundled)
    return _deep_merge_dict(bundled, overlay)


def merge_manifests(
    bundled: AgentTemplateManifest | None,
    overlay: AgentTemplateManifest | None,
) -> AgentTemplateManifest | None:
    """Merge bundled and overlay manifests into one validated model."""
    merged_payload = merge_manifest_payloads(
        bundled.model_dump() if bundled is not None else None,
        overlay.model_dump() if overlay is not None else None,
    )
    if merged_payload is None:
        return None
    return AgentTemplateManifest.model_validate(merged_payload)


def merge_manifest_layers(
    *layers: AgentTemplateManifest | None,
) -> AgentTemplateManifest | None:
    """Merge multiple manifest layers in order (later layers win)."""
    merged: AgentTemplateManifest | None = None
    for layer in layers:
        merged = merge_manifests(merged, layer)
    return merged


def resolve_template_source(
    *,
    bundled_exists: bool,
    overlay_exists: bool,
) -> AgentTemplateSource:
    """Classify catalog source from filesystem presence."""
    if bundled_exists and overlay_exists:
        return AgentTemplateSource.MERGED
    if overlay_exists:
        return AgentTemplateSource.OVERLAY
    return AgentTemplateSource.BUNDLED


def resolve_template_file(
    *,
    template_id: str,
    filename: str,
    bundled_dir: Path | None,
    overlay_dirs: list[Path] | None = None,
    overlay_dir: Path | None = None,
    shared_dir: Path | None,
) -> Path | None:
    """Resolve a template source file with overlay precedence."""
    _ = template_id
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError(f"invalid template filename: {filename!r}")

    resolved_overlay_dirs: list[Path] = list(overlay_dirs or [])
    if overlay_dir is not None:
        resolved_overlay_dirs.insert(0, overlay_dir)

    search_dirs: list[Path] = []
    for directory in resolved_overlay_dirs:
        search_dirs.append(directory)
        partials = directory / "_partials"
        if partials.is_dir():
            search_dirs.append(partials)
    if bundled_dir is not None:
        search_dirs.append(bundled_dir)
        partials = bundled_dir / "_partials"
        if partials.is_dir():
            search_dirs.append(partials)
    if shared_dir is not None:
        shared_partials = shared_dir / "_partials"
        if shared_partials.is_dir():
            search_dirs.append(shared_partials)

    for directory in search_dirs:
        direct = directory / filename
        if direct.is_file():
            return direct
        partial_name = f"{filename}.md.tpl" if not filename.endswith(".tpl") else filename
        partial_path = directory / partial_name
        if partial_path.is_file():
            return partial_path
        if not filename.endswith(".md.tpl"):
            named = directory / f"{filename}.md.tpl"
            if named.is_file():
                return named
    return None
