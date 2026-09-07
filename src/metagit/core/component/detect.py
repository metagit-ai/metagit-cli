#!/usr/bin/env python
"""Detect candidate components from filesystem markers and init one draft."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from metagit.core.component.catalog import ComponentCatalog
from metagit.core.component.models import Component
from metagit.core.component.paths import normalize_repo_relative_path
from metagit.core.config.component_validation import validate_components
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.layout_resolver import find_project, find_repo
from metagit.core.workspace.root_resolver import resolve_definition_root

_SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "dist",
        "build",
        ".venv",
        "__pycache__",
        ".tox",
        "vendor",
    }
)
_CONVENTION_KINDS: dict[str, str] = {
    "apps": "application",
    "packages": "package",
    "services": "service",
    "libs": "library",
    "internal": "library",
}
_INFRA_DIRS = frozenset({"infra", "terraform", "helm", "charts"})
_HIGH_MARKER_LANGUAGE: dict[str, str] = {
    "package.json": "typescript",
    "pyproject.toml": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
}
_LANGUAGE_RANK = {
    "rust": 0,
    "go": 1,
    "python": 2,
    "java": 3,
    "csharp": 4,
    "typescript": 5,
}
_MEDIUM_FILES = frozenset({"Dockerfile", "Taskfile.yml", "Makefile"})
_INFRA_FILES = frozenset({"Chart.yaml", "helmfile.yaml"})


class ComponentDetector:
    """Scan checkouts for component candidates and write drafts on apply."""

    def detect(
        self,
        config: MetagitConfig,
        *,
        project: str | None = None,
        repo: str | None = None,
        definition_root: str,
    ) -> dict[str, Any]:
        """Return candidate components for the selected repo checkouts."""
        catalogued = self._catalogued_paths(config)
        candidates: list[dict[str, Any]] = []
        for project_name, repo_name, checkout in self._scan_targets(
            config,
            project=project,
            repo=repo,
            definition_root=Path(definition_root),
        ):
            for row in self._scan_checkout(checkout):
                normalized = row["path"]
                already = (project_name, repo_name, normalized) in catalogued
                candidates.append(
                    {
                        **row,
                        "project": project_name,
                        "repo": repo_name,
                        "already_catalogued": already,
                    }
                )
        return {"candidates": candidates}

    def apply_candidates(
        self,
        config: MetagitConfig,
        candidates: list[dict[str, Any]],
        *,
        config_path: str,
    ) -> MetagitConfig | Exception:
        """Append valid new candidates to repos[].components[] and save once."""
        root = resolve_definition_root(config_path)
        added = 0
        for candidate in candidates:
            if candidate.get("already_catalogued"):
                continue
            repo_entry = self._workspace_repo(
                config,
                project=candidate.get("project"),
                repo=candidate.get("repo"),
            )
            if repo_entry is None:
                continue
            try:
                component = Component(
                    name=str(candidate.get("name") or ""),
                    path=str(candidate.get("path") or ""),
                    kind=candidate.get("kind"),
                    language=candidate.get("language"),
                )
            except Exception as exc:
                _ = exc
                continue
            repo_entry.components.append(component)
            issues = validate_components(config, definition_root=root)
            if issues:
                repo_entry.components.pop()
                continue
            added += 1
        if added == 0:
            return config
        manager = MetagitConfigManager(config_path=config_path)
        saved = manager.save_config(config)
        if isinstance(saved, Exception):
            return saved
        return config

    def init_component(
        self,
        config: MetagitConfig,
        path: str,
        *,
        name: str | None = None,
        kind: str | None = None,
        project: str | None = None,
        repo: str | None = None,
    ) -> Component | ValueError:
        """Build one declarative Component for a repository-relative path."""
        target = self._unique_target(config, project=project, repo=repo)
        if isinstance(target, ValueError):
            return target
        _, repo_name = target
        normalized = normalize_repo_relative_path(path)
        if isinstance(normalized, Exception):
            return normalized
        if name is not None and str(name).strip():
            comp_name = str(name).strip()
        elif normalized == ".":
            comp_name = repo_name
        else:
            comp_name = Path(normalized).name
        if not comp_name or "/" in comp_name:
            return ValueError("invalid component name")
        inferred_kind = kind or _kind_from_path(normalized)
        return Component(name=comp_name, path=normalized, kind=inferred_kind)

    def _scan_targets(
        self,
        config: MetagitConfig,
        *,
        project: str | None,
        repo: str | None,
        definition_root: Path,
    ) -> list[tuple[str, str, Path]]:
        targets: list[tuple[str, str, Path]] = []
        if config.workspace is not None:
            for workspace_project in config.workspace.projects:
                if project and workspace_project.name != project:
                    continue
                for entry in workspace_project.repos:
                    if repo and entry.name != repo:
                        continue
                    checkout = _repo_checkout(definition_root, entry.path)
                    targets.append((workspace_project.name, entry.name, checkout))
            return targets
        app_name = config.name
        if project and project != app_name:
            return []
        if repo and repo != app_name:
            return []
        return [(app_name, app_name, definition_root.resolve())]

    def _scan_checkout(self, checkout: Path) -> list[dict[str, Any]]:
        if not checkout.is_dir():
            return []
        found: list[dict[str, Any]] = []
        for current, dirnames, _ in os.walk(checkout, topdown=True):
            dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS]
            current_path = Path(current)
            if current_path.name in _CONVENTION_KINDS:
                kind = _CONVENTION_KINDS[current_path.name]
                for child_name in list(dirnames):
                    child = current_path / child_name
                    if not child.is_dir():
                        continue
                    row = _convention_candidate(child, checkout, kind)
                    if row is not None:
                        found.append(row)
            if current_path.name in _INFRA_DIRS and current_path != checkout:
                row = _infra_candidate(current_path, checkout)
                if row is not None:
                    found.append(row)
        for infra_name in sorted(_INFRA_DIRS):
            infra_dir = checkout / infra_name
            if infra_dir.is_dir():
                row = _infra_candidate(infra_dir, checkout)
                if row is not None:
                    found.append(row)
        return _drop_nested(found)

    def _catalogued_paths(self, config: MetagitConfig) -> set[tuple[str, str, str]]:
        indexed: set[tuple[str, str, str]] = set()
        for row in ComponentCatalog().list(config):
            normalized = normalize_repo_relative_path(row.spec.path)
            if isinstance(normalized, Exception):
                continue
            indexed.add((row.project, row.repo, normalized))
        return indexed

    def _workspace_repo(self, config: MetagitConfig, *, project: Any, repo: Any):
        if not isinstance(project, str) or not isinstance(repo, str):
            return None
        workspace_project = find_project(config, project)
        if workspace_project is None:
            return None
        return find_repo(workspace_project, repo)

    def _unique_target(
        self,
        config: MetagitConfig,
        *,
        project: str | None,
        repo: str | None,
    ) -> tuple[str, str] | ValueError:
        if config.workspace is None:
            return config.name, config.name
        matches: list[tuple[str, str]] = []
        for workspace_project in config.workspace.projects:
            if project and workspace_project.name != project:
                continue
            for entry in workspace_project.repos:
                if repo and entry.name != repo:
                    continue
                matches.append((workspace_project.name, entry.name))
        if project and repo:
            if len(matches) == 1:
                return matches[0]
            return ValueError(f"unknown project/repo {project}/{repo}")
        if len(matches) == 1:
            return matches[0]
        return ValueError("component init requires --project and --repo on umbrellas")


def _repo_checkout(definition_root: Path, repo_path: str | None) -> Path:
    rel = repo_path or "."
    candidate = Path(rel).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (definition_root / candidate).resolve()


def _convention_candidate(child: Path, checkout: Path, kind: str) -> dict[str, Any] | None:
    name = child.name
    if not name or "/" in name:
        return None
    relative = _relative_posix(child, checkout)
    if relative is None:
        return None
    markers, language, confidence = _inspect_markers(child)
    if not markers or confidence is None:
        return None
    return {
        "name": name,
        "path": relative,
        "kind": kind,
        "language": language,
        "confidence": confidence,
        "markers": markers,
    }


def _infra_candidate(directory: Path, checkout: Path) -> dict[str, Any] | None:
    name = directory.name
    if not name or "/" in name:
        return None
    relative = _relative_posix(directory, checkout)
    if relative is None:
        return None
    markers = _infra_markers(directory)
    if not markers:
        return None
    return {
        "name": name,
        "path": relative,
        "kind": "infrastructure",
        "language": None,
        "confidence": "high",
        "markers": markers,
    }


def _infra_markers(directory: Path) -> list[str]:
    markers: list[str] = []
    try:
        for entry in sorted(directory.iterdir()):
            if entry.is_file() and (entry.suffix == ".tf" or entry.name in _INFRA_FILES):
                markers.append(entry.name)
    except OSError:
        return []
    return markers


def _inspect_markers(directory: Path) -> tuple[list[str], str | None, str | None]:
    high: list[str] = []
    languages: list[str] = []
    for filename, language in _HIGH_MARKER_LANGUAGE.items():
        if (directory / filename).is_file():
            high.append(filename)
            languages.append(language)
    try:
        csproj_files = sorted(directory.glob("*.csproj"))
    except OSError:
        csproj_files = []
    for csproj in csproj_files:
        if csproj.is_file():
            high.append(csproj.name)
            languages.append("csharp")
    if (directory / "pyproject.toml").is_file() and (directory / "uv.lock").is_file():
        if "uv.lock" not in high:
            high.append("uv.lock")
        if "python" not in languages:
            languages.append("python")
    if high:
        return high, _best_language(languages), "high"
    medium = [name for name in sorted(_MEDIUM_FILES) if (directory / name).is_file()]
    if medium:
        return medium, None, "medium"
    return [], None, None


def _best_language(languages: list[str]) -> str | None:
    if not languages:
        return None
    return min(languages, key=lambda item: _LANGUAGE_RANK.get(item, 99))


def _kind_from_path(normalized: str) -> str | None:
    for part in normalized.split("/"):
        if part in _CONVENTION_KINDS:
            return _CONVENTION_KINDS[part]
        if part in _INFRA_DIRS:
            return "infrastructure"
    return None


def _relative_posix(path: Path, checkout: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(checkout.resolve()).as_posix()
    except ValueError:
        return None
    normalized = normalize_repo_relative_path(relative)
    if isinstance(normalized, Exception):
        return None
    return normalized


def _drop_nested(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    chosen: list[str] = []
    for row in sorted(candidates, key=lambda item: (item["path"].count("/"), item["path"])):
        path = row["path"]
        if any(path == parent or path.startswith(parent + "/") for parent in chosen):
            continue
        kept.append(row)
        chosen.append(path)
    return kept
