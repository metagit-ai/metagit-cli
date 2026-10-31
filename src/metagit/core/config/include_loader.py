#!/usr/bin/env python
"""Compose a .metagit.yml manifest from root-relative ``includes`` fragments."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from metagit.core.config.yaml_roundtrip import build_roundtrip_yaml

MAX_INCLUDE_DEPTH = 3

FRAGMENT_TOP_LEVEL = frozenset({"includes", "workspace", "graph", "documentation", "taskers"})
FRAGMENT_WORKSPACE_KEYS = frozenset({"projects", "description", "agent_instructions", "agent_profile"})
FRAGMENT_GRAPH_KEYS = frozenset({"nodes", "relationships", "metadata"})
_APPEND_LISTS = frozenset({("workspace", "projects"), ("graph", "nodes"), ("graph", "relationships")})
_CONTAINER_KEYS = frozenset({"workspace", "graph"})


@dataclass(frozen=True)
class SourceLocation:
    """File and 1-based line that contributed one manifest entry."""

    path: str
    line: int


@dataclass
class ManifestSourceMap:
    """Provenance for a composed manifest. Not part of ``model_dump``."""

    root_path: str
    root_dir: str
    locations: dict[str, SourceLocation] = field(default_factory=dict)
    index_locations: dict[tuple[str, int], SourceLocation] = field(default_factory=dict)
    include_patterns: dict[str, list[str]] = field(default_factory=dict)
    resolved_files: list[str] = field(default_factory=list)


@dataclass
class IncludeLoadResult:
    """Merged YAML mapping plus provenance. ``data`` has no ``includes`` keys."""

    data: dict[str, Any]
    source_map: ManifestSourceMap


class ManifestComposeError(Exception):
    """Include, merge, or validation failure with file:line details."""

    def __init__(
        self,
        message: str,
        *,
        errors: list[dict[str, Any]] | None = None,
        sources: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.errors = errors or [{"message": message, "file": None, "line": None}]
        self.sources = sources or []


def manifest_declares_includes(path: Path) -> bool:
    """Return True when ``path`` is a mapping that contains an ``includes`` key."""
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if "includes:" not in text:
        return False
    try:
        loaded = build_roundtrip_yaml().load(text)
    except Exception:
        return False
    return isinstance(loaded, dict) and "includes" in loaded


def resolved_manifest_files(path: Path) -> list[Path]:
    """Return the root manifest plus every fragment it includes.

    A missing file yields an empty list. A manifest without ``includes``, or one
    that fails to compose, yields just the root so callers can still stat it.
    """
    if not path.is_file():
        return []
    if not manifest_declares_includes(path):
        return [path.resolve()]
    composed = load_composed_manifest(path)
    if isinstance(composed, Exception):
        return [path.resolve()]
    return [Path(item) for item in composed.source_map.resolved_files]


def load_composed_manifest(path: Path) -> IncludeLoadResult | Exception:
    """Load ``path`` and merge included fragments. Returns an exception on failure."""
    try:
        composer = _Composer(path)
        failure = composer.load(path.resolve(), depth=0, parent=None, via_line=None)
        if failure is not None:
            return failure
        return IncludeLoadResult(data=composer.merged, source_map=composer.source_map)
    except Exception as exc:
        return exc


def map_validation_error(exc: ValidationError, source_map: ManifestSourceMap) -> ManifestComposeError:
    """Attach fragment file:line locations to a pydantic validation error."""
    errors: list[dict[str, Any]] = []
    messages: list[str] = []
    for item in exc.errors():
        loc = tuple(item.get("loc", ()))
        located = _lookup_loc(loc, source_map)
        message = str(item.get("msg") or "validation error")
        loc_text = ".".join(str(part) for part in loc)
        file_text = located.path if located is not None else _display(source_map.root_path, source_map.root_dir)
        line = located.line if located is not None else 1
        rendered = f"{file_text}:{line}: {loc_text}: {message}" if loc_text else f"{file_text}:{line}: {message}"
        messages.append(rendered)
        errors.append({"message": message, "file": file_text, "line": line, "loc": list(loc)})
    summary = "; ".join(messages) if messages else str(exc)
    return ManifestComposeError(summary, errors=errors, sources=_source_entries(source_map))


def project_identity(name: str) -> str:
    """Source-map key for a workspace project."""
    return f"workspace.projects[{name}]"


def node_identity(node_id: str) -> str:
    """Source-map key for a graph node."""
    return f"graph.nodes[{node_id}]"


def relationship_identity(key: str) -> str:
    """Source-map key for a graph relationship."""
    return f"graph.relationships[{key}]"


def node_key(item: dict[str, Any]) -> str:
    """Stable id for a graph node mapping."""
    identity = item.get("identity")
    if identity:
        return str(identity)
    name = item.get("name")
    if name:
        return str(name)
    return json.dumps(item, sort_keys=True, default=str)


def relationship_tuple(item: dict[str, Any]) -> tuple[str, str, str]:
    """Identity tuple used to reject duplicate relationships."""
    source = item.get("from")
    if source is None:
        source = item.get("from_endpoint")
    return (
        _endpoint_token(source),
        _endpoint_token(item.get("to")),
        str(item.get("type") or "depends_on"),
    )


def relationship_key(item: dict[str, Any]) -> str:
    """Source-map key material for one relationship."""
    ident = item.get("id")
    if ident:
        return str(ident)
    return json.dumps(relationship_tuple(item))


def slugify_name(name: str) -> str:
    """Turn a project or node name into a fragment filename stem."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot slugify name {name!r}")
    return slug


def _endpoint_token(value: Any) -> str:
    if not isinstance(value, dict):
        return "" if value is None else str(value)
    parts: list[str] = []
    for key in ("project", "repo", "path", "component", "identity"):
        item = value.get(key)
        if item not in (None, ""):
            parts.append(f"{key}={item}")
    return ",".join(parts)


def _display(path: str | Path, root_dir: str | Path) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(Path(root_dir).resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _source_entries(source_map: ManifestSourceMap) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for index, path in enumerate(source_map.resolved_files):
        entries.append(
            {
                "path": _display(path, source_map.root_dir),
                "role": "root" if index == 0 else "fragment",
            }
        )
    return entries


def _lookup_loc(loc: tuple[Any, ...], source_map: ManifestSourceMap) -> SourceLocation | None:
    pairs = (
        ("workspace", "projects", "workspace.projects"),
        ("graph", "nodes", "graph.nodes"),
        ("graph", "relationships", "graph.relationships"),
    )
    for head, child, key in pairs:
        if len(loc) >= 3 and loc[0] == head and loc[1] == child and isinstance(loc[2], int):
            found = source_map.index_locations.get((key, int(loc[2])))
            if found is not None:
                return SourceLocation(_display(found.path, source_map.root_dir), found.line)
    if loc:
        dotted = ".".join(str(part) for part in loc if not isinstance(part, int))
        for candidate in (dotted, str(loc[0])):
            found = source_map.locations.get(candidate)
            if found is not None:
                return SourceLocation(_display(found.path, source_map.root_dir), found.line)
    return None


def _key_line(node: CommentedMap, key: object) -> int:
    try:
        info = node.lc.key(key)
        if info and info[0] is not None:
            return int(info[0]) + 1
    except Exception:
        return 1
    return 1


def _item_line(seq: CommentedSeq, index: int) -> int:
    try:
        info = seq.lc.item(index)
        if info and info[0] is not None:
            return int(info[0]) + 1
    except Exception:
        return 1
    return 1


def _plain(value: Any) -> Any:
    if isinstance(value, str):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _is_glob(pattern: str) -> bool:
    return any(token in pattern for token in ("*", "?", "["))


def _is_url(pattern: str) -> bool:
    lowered = pattern.strip().lower()
    if "://" in lowered:
        return True
    return lowered.startswith(("http:", "https:", "file:", "git:"))


class _Composer:
    """One manifest load, including nested fragments."""

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path.expanduser().resolve()
        self.root_dir = self.root_path.parent
        self.source_map = ManifestSourceMap(root_path=str(self.root_path), root_dir=str(self.root_dir))
        self.merged: dict[str, Any] = {}
        self._seen: set[str] = set()
        self._stack: list[str] = []
        self._project_names: dict[str, SourceLocation] = {}
        self._node_ids: dict[str, SourceLocation] = {}
        self._relationship_ids: dict[str, SourceLocation] = {}
        self._relationship_tuples: dict[tuple[str, str, str], SourceLocation] = {}

    def load(
        self,
        path: Path,
        *,
        depth: int,
        parent: Path | None,
        via_line: int | None,
    ) -> ManifestComposeError | None:
        """Load one file and the fragments it includes."""
        resolved = path.resolve()
        key = str(resolved)
        if depth > MAX_INCLUDE_DEPTH:
            return self._error(
                f"include depth {depth} exceeds maximum {MAX_INCLUDE_DEPTH}",
                path=parent or resolved,
                line=via_line,
            )
        if key in self._stack:
            cycle = [_display(item, self.root_dir) for item in self._stack + [key]]
            return self._error(
                f"include cycle: {' -> '.join(cycle)}",
                path=parent or resolved,
                line=via_line,
            )
        if key in self._seen:
            return self._error(
                f"file included more than once: {_display(resolved, self.root_dir)}",
                path=parent or resolved,
                line=via_line,
            )
        self._seen.add(key)
        self._stack.append(key)
        self.source_map.resolved_files.append(key)
        try:
            if not resolved.is_file():
                return self._error(
                    f"include file not found: {_display(resolved, self.root_dir)}", path=resolved, line=1
                )
            try:
                loaded = build_roundtrip_yaml().load(resolved.read_text(encoding="utf-8"))
            except Exception as exc:
                return self._error(f"invalid YAML: {exc}", path=resolved, line=1)
            if loaded is None:
                loaded = CommentedMap()
            if not isinstance(loaded, CommentedMap):
                return self._error("manifest fragment must be a YAML mapping", path=resolved, line=1)
            entries = self._read_includes(loaded, resolved)
            if isinstance(entries, ManifestComposeError):
                return entries
            merged = self._merge_node(self.merged, loaded, file_path=resolved, is_fragment=depth > 0, key_prefix=())
            if merged is not None:
                return merged
            for pattern, line in entries:
                expanded = self._expand(pattern, including=resolved, line=line)
                if isinstance(expanded, ManifestComposeError):
                    return expanded
                for child in expanded:
                    failure = self.load(child, depth=depth + 1, parent=resolved, via_line=line)
                    if failure is not None:
                        return failure
            return None
        finally:
            self._stack.pop()

    def _read_includes(
        self,
        node: CommentedMap,
        file_path: Path,
    ) -> list[tuple[str, int]] | ManifestComposeError:
        if "includes" not in node:
            return []
        value = node.get("includes")
        line = _key_line(node, "includes")
        if not isinstance(value, CommentedSeq):
            return self._error("includes must be a list of relative paths or globs", path=file_path, line=line)
        entries: list[tuple[str, int]] = []
        for index, item in enumerate(value):
            item_line = _item_line(value, index)
            if not isinstance(item, str) or not str(item).strip():
                return self._error("include entry must be a non-empty string", path=file_path, line=item_line)
            entries.append((str(item).strip(), item_line))
        self.source_map.include_patterns[str(file_path.resolve())] = [pattern for pattern, _line in entries]
        return entries

    def _expand(self, pattern: str, *, including: Path, line: int) -> list[Path] | ManifestComposeError:
        if _is_url(pattern):
            return self._error(f"include URL is not allowed: {pattern}", path=including, line=line)
        if Path(pattern).is_absolute() or pattern.startswith(("/", "\\")):
            return self._error(f"include path is absolute: {pattern}", path=including, line=line)
        including_dir = including.parent
        if _is_glob(pattern):
            matches = [item for item in including_dir.glob(pattern) if item.is_file()]
            matches.sort(key=lambda item: self._sort_key(item))
            checked: list[Path] = []
            for match in matches:
                failure = self._confine(match, pattern=pattern, including=including, line=line)
                if failure is not None:
                    return failure
                checked.append(match)
            return checked
        candidate = including_dir / pattern
        if not candidate.exists():
            return self._error(f"include file not found: {pattern}", path=including, line=line)
        failure = self._confine(candidate, pattern=pattern, including=including, line=line)
        if failure is not None:
            return failure
        return [candidate]

    def _confine(self, candidate: Path, *, pattern: str, including: Path, line: int) -> ManifestComposeError | None:
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            return self._error(f"include path cannot be resolved: {pattern} ({exc})", path=including, line=line)
        try:
            resolved.relative_to(self.root_dir.resolve())
        except ValueError:
            if candidate.is_symlink() or _path_has_symlink(candidate, self.root_dir):
                return self._error(f"symlink escapes manifest root: {pattern}", path=including, line=line)
            return self._error(f"include path escapes manifest root: {pattern}", path=including, line=line)
        return None

    def _sort_key(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root_dir.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def _merge_node(
        self,
        base: dict[str, Any],
        node: CommentedMap,
        *,
        file_path: Path,
        is_fragment: bool,
        key_prefix: tuple[str, ...],
    ) -> ManifestComposeError | None:
        if is_fragment and not key_prefix:
            failure = self._reject_fragment_keys(node, file_path)
            if failure is not None:
                return failure
        for key in node:
            if key == "includes":
                continue
            value = node.get(key)
            path = key_prefix + (str(key),)
            ident = ".".join(path)
            line = _key_line(node, key)
            location = SourceLocation(str(file_path.resolve()), line)
            if path in _APPEND_LISTS:
                failure = self._append_list(base, path, value, file_path)
                if failure is not None:
                    return failure
                continue
            if str(key) in _CONTAINER_KEYS and not key_prefix and isinstance(value, CommentedMap):
                if key not in base or base[key] is None:
                    base[str(key)] = {}
                elif not isinstance(base[key], dict):
                    return self._exclusive_error(ident, location)
                failure = self._merge_node(
                    base[str(key)],
                    value,
                    file_path=file_path,
                    is_fragment=is_fragment,
                    key_prefix=path,
                )
                if failure is not None:
                    return failure
                continue
            if key in base and base[key] is not None:
                return self._exclusive_error(ident, location)
            base[str(key)] = _plain(value)
            self.source_map.locations[ident] = location
        return None

    def _reject_fragment_keys(self, node: CommentedMap, file_path: Path) -> ManifestComposeError | None:
        for key in node:
            if str(key) in FRAGMENT_TOP_LEVEL:
                continue
            return self._error(
                f"fragment key {str(key)!r} is not allowed",
                path=file_path,
                line=_key_line(node, key),
            )
        workspace = node.get("workspace")
        if workspace is not None:
            if not isinstance(workspace, CommentedMap):
                return self._error(
                    "fragment workspace must be a mapping", path=file_path, line=_key_line(node, "workspace")
                )
            for key in workspace:
                if str(key) not in FRAGMENT_WORKSPACE_KEYS:
                    return self._error(
                        f"fragment key 'workspace.{key}' is not allowed",
                        path=file_path,
                        line=_key_line(workspace, key),
                    )
        graph = node.get("graph")
        if graph is not None:
            if not isinstance(graph, CommentedMap):
                return self._error("fragment graph must be a mapping", path=file_path, line=_key_line(node, "graph"))
            for key in graph:
                if str(key) not in FRAGMENT_GRAPH_KEYS:
                    return self._error(
                        f"fragment key 'graph.{key}' is not allowed",
                        path=file_path,
                        line=_key_line(graph, key),
                    )
        return None

    def _append_list(
        self,
        base: dict[str, Any],
        path: tuple[str, ...],
        value: Any,
        file_path: Path,
    ) -> ManifestComposeError | None:
        key = path[-1]
        if not isinstance(value, CommentedSeq):
            return self._error(
                f"{'.'.join(path)} must be a list",
                path=file_path,
                line=1,
            )
        current = base.get(key)
        if current is None:
            current = []
            base[key] = current
        elif not isinstance(current, list):
            return self._exclusive_error(".".join(path), SourceLocation(str(file_path.resolve()), 1))
        list_name = ".".join(path)
        for index, item in enumerate(value):
            line = _item_line(value, index)
            plain = _plain(item)
            location = SourceLocation(str(file_path.resolve()), line)
            failure = self._reject_duplicate(list_name, plain, location)
            if failure is not None:
                return failure
            merged_index = len(current)
            self.source_map.index_locations[(list_name, merged_index)] = location
            if isinstance(plain, dict):
                self._remember_item(list_name, plain, location)
            current.append(plain)
        return None

    def _reject_duplicate(
        self,
        list_name: str,
        item: Any,
        location: SourceLocation,
    ) -> ManifestComposeError | None:
        if not isinstance(item, dict):
            return None
        if list_name == "workspace.projects" and item.get("name") is not None:
            name = str(item["name"])
            previous = self._project_names.get(name)
            if previous is not None:
                return self._duplicate(
                    f"duplicate project name {name!r}",
                    previous,
                    location,
                )
        if list_name == "graph.nodes":
            ident = node_key(item)
            previous = self._node_ids.get(ident)
            if previous is not None:
                return self._duplicate(f"duplicate graph node id {ident!r}", previous, location)
        if list_name == "graph.relationships":
            tuple_key = relationship_tuple(item)
            previous_tuple = self._relationship_tuples.get(tuple_key)
            if previous_tuple is not None:
                return self._duplicate("duplicate graph relationship", previous_tuple, location)
            ident = item.get("id")
            if ident is not None:
                previous_id = self._relationship_ids.get(str(ident))
                if previous_id is not None:
                    return self._duplicate(
                        f"duplicate graph relationship id {str(ident)!r}",
                        previous_id,
                        location,
                    )
        return None

    def _remember_item(self, list_name: str, item: dict[str, Any], location: SourceLocation) -> None:
        if list_name == "workspace.projects" and item.get("name") is not None:
            name = str(item["name"])
            self._project_names[name] = location
            self.source_map.locations[project_identity(name)] = location
        elif list_name == "graph.nodes":
            ident = node_key(item)
            self._node_ids[ident] = location
            self.source_map.locations[node_identity(ident)] = location
        elif list_name == "graph.relationships":
            self._relationship_tuples[relationship_tuple(item)] = location
            ident = item.get("id")
            key = str(ident) if ident is not None else relationship_key(item)
            if ident is not None:
                self._relationship_ids[str(ident)] = location
            self.source_map.locations[relationship_identity(key)] = location

    def _duplicate(
        self,
        message: str,
        previous: SourceLocation,
        current: SourceLocation,
    ) -> ManifestComposeError:
        first = f"{_display(previous.path, self.root_dir)}:{previous.line}"
        second = f"{_display(current.path, self.root_dir)}:{current.line}"
        text = f"{message} in {first} and {second}"
        return self._error(text, path=Path(current.path), line=current.line)

    def _exclusive_error(self, ident: str, location: SourceLocation) -> ManifestComposeError:
        previous = self.source_map.locations.get(ident)
        current = f"{_display(location.path, self.root_dir)}:{location.line}"
        if previous is None:
            text = f"{ident} is defined more than once ({current})"
        else:
            first = f"{_display(previous.path, self.root_dir)}:{previous.line}"
            text = f"{ident} is defined in both {first} and {current}"
        return self._error(text, path=Path(location.path), line=location.line)

    def _error(self, message: str, *, path: Path | None, line: int | None) -> ManifestComposeError:
        file_text = _display(path, self.root_dir) if path is not None else None
        rendered = f"{file_text}:{line}: {message}" if file_text and line else message
        return ManifestComposeError(
            rendered,
            errors=[{"message": message, "file": file_text, "line": line}],
            sources=_source_entries(self.source_map),
        )


def _path_has_symlink(candidate: Path, root_dir: Path) -> bool:
    current = candidate
    root = root_dir.resolve()
    while True:
        if current.is_symlink():
            return True
        if current.resolve() == root or current == current.parent:
            return False
        current = current.parent
