#!/usr/bin/env python
"""Write a composed manifest back to the files it was loaded from."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from metagit.core.config.format_service import build_metagit_payload
from metagit.core.config.include_loader import (
    ManifestComposeError,
    ManifestSourceMap,
    SourceLocation,
    load_composed_manifest,
    map_validation_error,
    node_identity,
    node_key,
    project_identity,
    relationship_identity,
    relationship_key,
    slugify_name,
)
from metagit.core.config.models import MetagitConfig
from metagit.core.config.schema_urls import (
    METAGIT_CONFIG_SCHEMA_URL,
    METAGIT_FRAGMENT_SCHEMA_URL,
)
from metagit.core.config.yaml_edit_diff import diff_payloads
from metagit.core.config.yaml_edit_types import YamlEdit
from metagit.core.config.yaml_order import order_payload
from metagit.core.config.yaml_roundtrip import build_roundtrip_yaml, format_yaml_document
from metagit.core.config.yaml_save import splice_files
from metagit.core.utils.yaml_class import yaml as plain_yaml

_PROJECT_PREFIX = "workspace.projects["
_NODE_PREFIX = "graph.nodes["
_RELATIONSHIP_PREFIX = "graph.relationships["


@dataclass
class SplitPlan:
    """Files a split would create or refresh."""

    root: str
    files: list[str]
    dry_run: bool
    changed: bool


def save_partitioned(
    config: MetagitConfig,
    source_map: ManifestSourceMap,
    baseline: dict[str, str] | None,
    *,
    include_defaults: bool = False,
    auto_format: bool = True,
) -> tuple[ManifestSourceMap, dict[str, str]] | Exception:
    """Write each originating file. Skip files whose partition did not change.

    A file that exists is spliced: only the nodes that differ from what is on disk
    are rewritten. A file that does not exist is rendered whole. Every new text is
    built before any file is written. ``baseline`` is the signature set recorded at
    load; the comparison now runs against the files on disk instead.
    """
    _ = baseline
    try:
        payload = build_metagit_payload(config, include_defaults=include_defaults)
        disk = _load_disk_state(Path(source_map.root_path))
        if isinstance(disk, Exception):
            return disk
        parts = partition_payload(payload, source_map)
        if isinstance(parts, Exception):
            return parts
        before_parts = _disk_partitions(disk, include_defaults=include_defaults)
        if isinstance(before_parts, Exception):
            return before_parts
        before_signatures = _signatures(before_parts)
        signatures = _signatures(parts)
        pending: list[tuple[Path, str]] = []
        edits_by_file: dict[str, list[YamlEdit]] = {}
        originals: dict[str, str] = {}
        for path, part in parts.items():
            target = Path(path)
            if not target.is_file() or disk is None:
                rendered = _render_part(
                    target,
                    part,
                    source_map=source_map,
                    include_defaults=include_defaults,
                    auto_format=auto_format,
                )
                original = target.read_text(encoding="utf-8") if target.is_file() else ""
                if rendered != original:
                    pending.append((target, rendered))
                continue
            if before_signatures.get(path) == signatures.get(path):
                continue
            edits = diff_payloads(before_parts.get(path, {}), part)
            if isinstance(edits, Exception):
                return edits
            if edits:
                edits_by_file[path] = edits
                originals[path] = target.read_text(encoding="utf-8")
        spliced = splice_files(edits_by_file, originals)
        if isinstance(spliced, Exception):
            return spliced
        pending.extend((Path(path), text) for path, text in spliced.items())
        for target, rendered in pending:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
        _sync_source_map(source_map, parts)
        return source_map, signatures
    except Exception as exc:
        return exc


def _load_disk_state(root: Path) -> tuple[MetagitConfig, ManifestSourceMap] | None | Exception:
    """Load the manifest as it is on disk, or None when the root file is missing."""
    if not root.is_file():
        return None
    composed = load_composed_manifest(root)
    if isinstance(composed, Exception):
        return composed
    try:
        return MetagitConfig(**composed.data), composed.source_map
    except ValidationError as exc:
        return map_validation_error(exc, composed.source_map)


def _disk_partitions(
    disk: tuple[MetagitConfig, ManifestSourceMap] | None,
    *,
    include_defaults: bool,
) -> dict[str, dict[str, Any]] | Exception:
    """Partition the on-disk manifest the same way a save partitions the new one."""
    if disk is None:
        return {}
    model, disk_map = disk
    return partition_payload(build_metagit_payload(model, include_defaults=include_defaults), disk_map)


def load_baseline(path: Path) -> tuple[ManifestSourceMap, dict[str, str]] | Exception:
    """Load provenance and per-file signatures for the manifest currently on disk."""
    composed = load_composed_manifest(path)
    if isinstance(composed, Exception):
        return composed
    try:
        model = MetagitConfig(**composed.data)
    except ValidationError as exc:
        return map_validation_error(exc, composed.source_map)
    return signatures_for(model, composed.source_map)


def signatures_for(
    config: MetagitConfig,
    source_map: ManifestSourceMap,
    *,
    include_defaults: bool = False,
) -> tuple[ManifestSourceMap, dict[str, str]] | Exception:
    """Return partition signatures for ``config`` without writing."""
    try:
        payload = build_metagit_payload(config, include_defaults=include_defaults)
        parts = partition_payload(payload, source_map)
        if isinstance(parts, Exception):
            return parts
        return source_map, _signatures(parts)
    except Exception as exc:
        return exc


def partition_payload(
    payload: dict[str, Any],
    source_map: ManifestSourceMap,
) -> dict[str, dict[str, Any]] | Exception:
    """Split a format payload into one mapping per originating file."""
    parts: dict[str, dict[str, Any]] = {path: {} for path in source_map.resolved_files}
    for key, value in payload.items():
        if key in {"workspace", "graph", "includes"}:
            continue
        owner = _owner_for_key(source_map, key)
        parts.setdefault(owner, {})[key] = value

    workspace = payload.get("workspace")
    if isinstance(workspace, dict):
        failure = _partition_workspace(workspace, source_map, parts)
        if failure is not None:
            return failure
    graph = payload.get("graph")
    if isinstance(graph, dict):
        failure = _partition_graph(graph, source_map, parts)
        if failure is not None:
            return failure
    for path, patterns in source_map.include_patterns.items():
        if patterns:
            parts.setdefault(path, {})["includes"] = list(patterns)
    return parts


def render_partition(
    path: Path,
    part: dict[str, Any],
    source_map: ManifestSourceMap,
    *,
    include_defaults: bool = False,
    auto_format: bool = True,
) -> str:
    """Render one file partition with the same formatter ``save_config`` uses."""
    return _render_part(
        path,
        part,
        source_map=source_map,
        include_defaults=include_defaults,
        auto_format=auto_format,
    )


def split_manifest(
    path: Path,
    *,
    by: str,
    directory: Path,
    dry_run: bool,
) -> SplitPlan | Exception:
    """Move projects and/or graph lists out of a single manifest into fragments."""
    try:
        root = path.expanduser().resolve()
        if not root.is_file():
            return FileNotFoundError(f"Configuration file not found: {root}")
        target_dir = directory if directory.is_absolute() else root.parent / directory
        try:
            target_dir.resolve().relative_to(root.parent.resolve())
        except ValueError:
            return ManifestComposeError(f"split directory escapes the manifest root: {directory}")
        yaml = build_roundtrip_yaml()
        document = yaml.load(root.read_text(encoding="utf-8"))
        if not isinstance(document, CommentedMap):
            return ManifestComposeError("manifest must be a YAML mapping")
        planned: list[Path] = []
        changed = False
        if by in {"project", "all"}:
            outcome = _split_projects(document, root=root, directory=target_dir, dry_run=dry_run, planned=planned)
            if isinstance(outcome, Exception):
                return outcome
            changed = changed or outcome
        if by in {"graph", "all"}:
            outcome = _split_graph(document, root=root, directory=target_dir, dry_run=dry_run, planned=planned)
            if isinstance(outcome, Exception):
                return outcome
            changed = changed or outcome
        if changed and not dry_run:
            _dump_roundtrip(yaml, document, root)
        return SplitPlan(
            root=str(root),
            files=[str(item) for item in planned],
            dry_run=dry_run,
            changed=changed and not dry_run,
        )
    except Exception as exc:
        return exc


def flatten_manifest(
    path: Path,
    *,
    output: Path | None = None,
    in_place: bool = False,
) -> str | Exception:
    """Return the merged manifest as one YAML document.

    A manifest without ``includes`` is returned unchanged and is not rewritten.
    """
    try:
        root = path.expanduser().resolve()
        original = root.read_text(encoding="utf-8")
        from metagit.core.config.include_loader import manifest_declares_includes
        from metagit.core.config.manager import MetagitConfigManager

        if not manifest_declares_includes(root):
            if output is not None and output.resolve() != root:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(original, encoding="utf-8")
            return original
        manager = MetagitConfigManager(config_path=root)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            return loaded
        from metagit.core.config.format_service import ConfigFormatService

        rendered = ConfigFormatService().render_metagit(loaded, original_text="")
        destination = root if in_place else output
        if destination is not None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered, encoding="utf-8")
        return rendered
    except Exception as exc:
        return exc


def _partition_workspace(
    workspace: dict[str, Any],
    source_map: ManifestSourceMap,
    parts: dict[str, dict[str, Any]],
) -> Exception | None:
    for key, value in workspace.items():
        if key == "projects":
            continue
        owner = _owner_for_key(source_map, f"workspace.{key}")
        parts.setdefault(owner, {}).setdefault("workspace", {})[key] = value
    projects = workspace.get("projects") or []
    owners: dict[str, list[Any]] = {}
    if isinstance(projects, list):
        for project in projects:
            if not isinstance(project, dict) or project.get("name") is None:
                owner = source_map.root_path
            else:
                name = str(project["name"])
                located = source_map.locations.get(project_identity(name))
                if located is None:
                    placed = _place_new_project(name, source_map)
                    if isinstance(placed, Exception):
                        return placed
                    owner = placed
                else:
                    owner = str(Path(located.path).resolve())
            owners.setdefault(owner, []).append(project)
    for path, items in owners.items():
        parts.setdefault(path, {}).setdefault("workspace", {})["projects"] = items
    for path in _files_with_prefix(source_map, _PROJECT_PREFIX):
        if path not in owners:
            parts.setdefault(path, {}).setdefault("workspace", {})["projects"] = []
    return None


def _partition_graph(
    graph: dict[str, Any],
    source_map: ManifestSourceMap,
    parts: dict[str, dict[str, Any]],
) -> Exception | None:
    for key, value in graph.items():
        if key in {"nodes", "relationships"}:
            continue
        owner = _owner_for_key(source_map, f"graph.{key}")
        parts.setdefault(owner, {}).setdefault("graph", {})[key] = value
    failure = _partition_named_list(
        graph.get("nodes") or [],
        source_map=source_map,
        parts=parts,
        prefix=_NODE_PREFIX,
        container="graph",
        list_key="nodes",
        identify=node_key,
        identity_for=node_identity,
    )
    if failure is not None:
        return failure
    return _partition_named_list(
        graph.get("relationships") or [],
        source_map=source_map,
        parts=parts,
        prefix=_RELATIONSHIP_PREFIX,
        container="graph",
        list_key="relationships",
        identify=relationship_key,
        identity_for=relationship_identity,
    )


def _partition_named_list(
    items: Any,
    *,
    source_map: ManifestSourceMap,
    parts: dict[str, dict[str, Any]],
    prefix: str,
    container: str,
    list_key: str,
    identify: Any,
    identity_for: Any,
) -> Exception | None:
    owners: dict[str, list[Any]] = {}
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                owner = source_map.root_path
            else:
                ident = identity_for(identify(item))
                located = source_map.locations.get(ident)
                if located is None:
                    placed = _place_new_graph_item(prefix, identify(item), source_map)
                    if isinstance(placed, Exception):
                        return placed
                    owner = placed
                else:
                    owner = str(Path(located.path).resolve())
            owners.setdefault(owner, []).append(item)
    for path, grouped in owners.items():
        parts.setdefault(path, {}).setdefault(container, {})[list_key] = grouped
    for path in _files_with_prefix(source_map, prefix):
        if path not in owners:
            parts.setdefault(path, {}).setdefault(container, {})[list_key] = []
    return None


def _place_new_project(name: str, source_map: ManifestSourceMap) -> str | Exception:
    if not _one_entry_per_file(source_map, _PROJECT_PREFIX):
        return source_map.root_path
    return _place_new_file(name, source_map, _PROJECT_PREFIX)


def _place_new_graph_item(prefix: str, label: str, source_map: ManifestSourceMap) -> str | Exception:
    owners = _files_with_prefix(source_map, prefix)
    if len(owners) == 1:
        return owners[0]
    if _one_entry_per_file(source_map, prefix):
        return _place_new_file(label, source_map, prefix)
    return source_map.root_path


def _place_new_file(name: str, source_map: ManifestSourceMap, prefix: str) -> str | Exception:
    try:
        slug = slugify_name(name)
    except ValueError as exc:
        return ManifestComposeError(str(exc))
    destination = (_first_include_dir(source_map) / f"{slug}.yml").resolve()
    owners = _names_at(source_map, destination, prefix)
    if owners and name not in owners:
        return ManifestComposeError(
            f"fragment collision for {name!r}: {destination.name} already contains {owners[0]!r}"
        )
    if destination.exists() and not owners:
        return ManifestComposeError(f"fragment already exists: {destination}")
    failure = _ensure_included(source_map, destination)
    if failure is not None:
        return failure
    return str(destination)


def _ensure_included(source_map: ManifestSourceMap, destination: Path) -> Exception | None:
    relative = destination.resolve().relative_to(Path(source_map.root_dir).resolve()).as_posix()
    patterns = source_map.include_patterns.setdefault(source_map.root_path, [])
    root_dir = Path(source_map.root_dir)
    for pattern in patterns:
        if _pattern_matches(pattern, relative, root_dir):
            return None
    patterns.append(relative)
    return None


def _pattern_matches(pattern: str, relative: str, root_dir: Path) -> bool:
    if any(token in pattern for token in ("*", "?", "[")):
        return Path(relative).match(pattern) or Path(relative).match(Path(pattern).name)
    return pattern == relative and (root_dir / relative).as_posix().endswith(relative)


def _one_entry_per_file(source_map: ManifestSourceMap, prefix: str) -> bool:
    counts: dict[str, int] = {}
    for ident, location in source_map.locations.items():
        if not ident.startswith(prefix):
            continue
        path = str(Path(location.path).resolve())
        counts[path] = counts.get(path, 0) + 1
    if not counts:
        return False
    return all(count == 1 for count in counts.values())


def _files_with_prefix(source_map: ManifestSourceMap, prefix: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for ident, location in source_map.locations.items():
        if not ident.startswith(prefix):
            continue
        path = str(Path(location.path).resolve())
        if path in seen:
            continue
        seen.add(path)
        found.append(path)
    return found


def _names_at(source_map: ManifestSourceMap, destination: Path, prefix: str) -> list[str]:
    resolved = str(destination.resolve())
    names: list[str] = []
    opener = prefix
    for ident, location in source_map.locations.items():
        if not ident.startswith(opener) or not ident.endswith("]"):
            continue
        if str(Path(location.path).resolve()) != resolved:
            continue
        names.append(ident[len(opener) : -1])
    return names


def _first_include_dir(source_map: ManifestSourceMap) -> Path:
    patterns = source_map.include_patterns.get(source_map.root_path) or []
    root_dir = Path(source_map.root_dir)
    if not patterns:
        return root_dir
    return (root_dir / Path(patterns[0]).parent).resolve()


def _owner_for_key(source_map: ManifestSourceMap, key: str) -> str:
    located = source_map.locations.get(key)
    if located is None:
        return source_map.root_path
    return str(Path(located.path).resolve())


def _render_part(
    path: Path,
    part: dict[str, Any],
    *,
    source_map: ManifestSourceMap,
    include_defaults: bool,
    auto_format: bool,
) -> str:
    if not auto_format:
        stream = StringIO()
        plain_yaml.dump(part, stream, sort_keys=False)
        text = stream.getvalue()
        return text if text.endswith("\n") else f"{text}\n"
    ordered = order_payload(part, MetagitConfig)
    if not isinstance(ordered, dict):
        ordered = {}
    original = path.read_text(encoding="utf-8") if path.is_file() else ""
    schema_url = (
        METAGIT_CONFIG_SCHEMA_URL
        if path.resolve() == Path(source_map.root_path).resolve()
        else METAGIT_FRAGMENT_SCHEMA_URL
    )
    return format_yaml_document(
        original,
        ordered,
        MetagitConfig,
        schema_url=schema_url,
        strip_absent_model_fields=not include_defaults,
    )


def _signatures(parts: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {path: json.dumps(part, sort_keys=True, default=str) for path, part in parts.items()}


def _sync_source_map(source_map: ManifestSourceMap, parts: dict[str, dict[str, Any]]) -> None:
    current_projects: set[str] = set()
    current_nodes: set[str] = set()
    current_relationships: set[str] = set()
    for path, part in parts.items():
        resolved = str(Path(path).resolve())
        if resolved not in source_map.resolved_files:
            source_map.resolved_files.append(resolved)
        workspace = part.get("workspace") if isinstance(part.get("workspace"), dict) else {}
        for project in workspace.get("projects") or []:
            if isinstance(project, dict) and project.get("name") is not None:
                ident = project_identity(str(project["name"]))
                current_projects.add(ident)
                source_map.locations.setdefault(ident, SourceLocation(resolved, 1))
        graph = part.get("graph") if isinstance(part.get("graph"), dict) else {}
        for node in graph.get("nodes") or []:
            if isinstance(node, dict):
                ident = node_identity(node_key(node))
                current_nodes.add(ident)
                source_map.locations.setdefault(ident, SourceLocation(resolved, 1))
        for relationship in graph.get("relationships") or []:
            if isinstance(relationship, dict):
                ident = relationship_identity(relationship_key(relationship))
                current_relationships.add(ident)
                source_map.locations.setdefault(ident, SourceLocation(resolved, 1))
    for ident in list(source_map.locations):
        drop_project = ident.startswith(_PROJECT_PREFIX) and ident not in current_projects
        drop_node = ident.startswith(_NODE_PREFIX) and ident not in current_nodes
        drop_edge = ident.startswith(_RELATIONSHIP_PREFIX) and ident not in current_relationships
        if drop_project or drop_node or drop_edge:
            del source_map.locations[ident]


def _split_projects(
    document: CommentedMap,
    *,
    root: Path,
    directory: Path,
    dry_run: bool,
    planned: list[Path],
) -> bool | Exception:
    workspace = document.get("workspace")
    projects = workspace.get("projects") if isinstance(workspace, CommentedMap) else None
    if not isinstance(projects, CommentedSeq) or len(projects) == 0:
        return False
    slugs: dict[str, str] = {}
    destinations: list[tuple[Any, Path]] = []
    for item in projects:
        if not isinstance(item, CommentedMap) or item.get("name") is None:
            return ManifestComposeError("cannot split a project that has no name")
        name = str(item.get("name"))
        try:
            slug = slugify_name(name)
        except ValueError as exc:
            return ManifestComposeError(str(exc))
        if slug in slugs:
            return ManifestComposeError(
                f"project name slug collision: {slugs[slug]!r} and {name!r} both map to {slug}.yml"
            )
        slugs[slug] = name
        destination = directory / "projects" / f"{slug}.yml"
        existing = _fragment_project_names(destination)
        if isinstance(existing, Exception):
            return existing
        if existing and existing != [name]:
            return ManifestComposeError(
                f"fragment collision for project {name!r}: {destination.name} already contains {existing[0]!r}"
            )
        destinations.append((item, destination))
        planned.append(destination)
    if dry_run:
        return False
    changed = False
    for item, destination in destinations:
        if _fragment_project_names(destination) == [str(item.get("name"))]:
            continue
        failure = _write_list_fragment(destination, section="workspace", key="projects", items=[copy.deepcopy(item)])
        if failure is not None:
            return failure
        changed = True
    workspace.pop("projects")
    if len(workspace) == 0:
        document.pop("workspace")
    relative = directory.resolve().relative_to(root.parent.resolve()).as_posix()
    _append_includes(document, [f"{relative}/projects/{destination.name}" for _item, destination in destinations])
    return True if changed or "includes" in document else changed


def _split_graph(
    document: CommentedMap,
    *,
    root: Path,
    directory: Path,
    dry_run: bool,
    planned: list[Path],
) -> bool | Exception:
    graph = document.get("graph")
    if not isinstance(graph, CommentedMap):
        return False
    sections = (
        ("nodes", directory / "graph" / "nodes.yml"),
        ("relationships", directory / "graph" / "relationships.yml"),
    )
    present = [
        (key, dest) for key, dest in sections if isinstance(graph.get(key), CommentedSeq) and len(graph.get(key)) > 0
    ]
    if not present:
        return False
    for _key, destination in present:
        planned.append(destination)
    if dry_run:
        return False
    relative_paths: list[str] = []
    relative_dir = directory.resolve().relative_to(root.parent.resolve()).as_posix()
    for key, destination in present:
        items = [copy.deepcopy(item) for item in graph.get(key)]
        if not destination.is_file():
            failure = _write_list_fragment(destination, section="graph", key=key, items=items)
            if failure is not None:
                return failure
        graph.pop(key)
        relative_paths.append(f"{relative_dir}/graph/{destination.name}")
    if len(graph) == 0:
        document.pop("graph")
    _append_includes(document, relative_paths)
    return True


def _fragment_project_names(path: Path) -> list[str] | Exception:
    if not path.is_file():
        return []
    try:
        loaded = build_roundtrip_yaml().load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return exc
    if not isinstance(loaded, CommentedMap):
        return []
    workspace = loaded.get("workspace")
    if not isinstance(workspace, CommentedMap):
        return []
    projects = workspace.get("projects")
    if not isinstance(projects, CommentedSeq):
        return []
    return [
        str(item.get("name")) for item in projects if isinstance(item, CommentedMap) and item.get("name") is not None
    ]


def _write_list_fragment(path: Path, *, section: str, key: str, items: list[Any]) -> Exception | None:
    try:
        sequence = CommentedSeq()
        for item in items:
            sequence.append(item)
        body_section = CommentedMap()
        body_section[key] = sequence
        body = CommentedMap()
        body[section] = body_section
        from metagit.core.config.schema_urls import schema_language_server_directive

        body.yaml_set_start_comment(f"{schema_language_server_directive(METAGIT_FRAGMENT_SCHEMA_URL)}\n")
        path.parent.mkdir(parents=True, exist_ok=True)
        _dump_roundtrip(build_roundtrip_yaml(), body, path)
        return None
    except Exception as exc:
        return exc


def _append_includes(document: CommentedMap, patterns: list[str]) -> None:
    existing = [str(item) for item in document.get("includes") or []]
    for pattern in patterns:
        if pattern not in existing:
            existing.append(pattern)
    if "includes" in document:
        document["includes"] = existing
        return
    document.insert(0, "includes", existing)


def _dump_roundtrip(yaml: Any, document: CommentedMap, path: Path) -> None:
    stream = StringIO()
    yaml.dump(document, stream)
    text = stream.getvalue()
    path.write_text(text if text.endswith("\n") else f"{text}\n", encoding="utf-8")
