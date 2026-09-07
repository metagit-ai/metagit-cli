#!/usr/bin/env python
"""Create and maintain derived workspace projects within one umbrella manifest."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from metagit.core.component.graph import ComponentGraphService
from metagit.core.component.models import Component
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import DerivedFromRef, ProjectPath
from metagit.core.workspace.catalog_models import CatalogError
from metagit.core.workspace.derived_models import DerivedMutationResult
from metagit.core.workspace.layout_resolver import find_project, find_repo, validate_layout_name
from metagit.core.workspace.models import (
    DerivedProjectConfig,
    DerivedSourceScope,
    ProjectDedupeOverride,
    Workspace,
    WorkspaceProject,
)
from metagit.core.workspace.protection import project_is_protected, repo_is_protected
from metagit.core.workspace.root_resolver import reserved_project_names
from metagit.core.workspace.workspace_dedupe import find_duplicate_identities

# Identity fields copied from source on create/refresh (not local posture).
_IDENTITY_FIELDS = (
    "description",
    "ref",
    "path",
    "branches",
    "url",
    "sync",
    "language",
    "language_version",
    "package_manager",
    "frameworks",
    "source_provider",
    "source_namespace",
    "source_repo_id",
    "source_id",
)


def _utc_now_iso() -> str:
    """Return current UTC time as ISO-8601."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _merge_tags(source_tags: dict[str, str], local_tags: dict[str, str]) -> dict[str, str]:
    """Overwrite overlapping tags from source; keep local-only keys."""
    merged = dict(source_tags)
    for key, value in local_tags.items():
        if key not in source_tags:
            merged[key] = value
    return merged


def _copy_components(
    source: ProjectPath,
    component_names: Optional[list[str]] = None,
) -> list[Component]:
    """Deep-copy source components, optionally filtered to an allow-list."""
    wanted = None if component_names is None else set(component_names)
    copied: list[Component] = []
    for item in source.components:
        if wanted is not None and item.name not in wanted:
            continue
        copied.append(item.model_copy(deep=True))
    return copied


def _copy_identity_from_source(
    source: ProjectPath,
    *,
    name: str,
    derived_from: DerivedFromRef,
    local_tags: Optional[dict[str, str]] = None,
    agent_instructions: Optional[str] = None,
    agent_profile: Optional[object] = None,
    protected: Optional[bool] = None,
    component_names: Optional[list[str]] = None,
) -> ProjectPath:
    """Build a derived ProjectPath from a source entry."""
    payload: dict[str, object] = {"name": name}
    for field in _IDENTITY_FIELDS:
        payload[field] = getattr(source, field)
    payload["tags"] = _merge_tags(dict(source.tags), dict(local_tags or {}))
    payload["derived_from"] = derived_from
    payload["components"] = _copy_components(source, component_names)
    if agent_instructions is not None:
        payload["agent_instructions"] = agent_instructions
    elif source.agent_instructions is not None:
        payload["agent_instructions"] = source.agent_instructions
    if agent_profile is not None:
        payload["agent_profile"] = agent_profile
    elif source.agent_profile is not None:
        payload["agent_profile"] = source.agent_profile
    payload["protected"] = protected if protected is not None else bool(source.protected)
    return ProjectPath.model_validate(payload)


def _refresh_identity(
    target: ProjectPath,
    source: ProjectPath,
    component_names: Optional[list[str]] = None,
) -> ProjectPath:
    """Re-pull identity fields from source while preserving local membership/posture."""
    data = target.model_dump(mode="python")
    for field in _IDENTITY_FIELDS:
        data[field] = getattr(source, field)
    data["tags"] = _merge_tags(dict(source.tags), dict(target.tags))
    data["components"] = _copy_components(source, component_names)
    derived = target.derived_from
    if derived is None:
        raise ValueError(f"repo '{target.name}' is missing derived_from provenance")
    data["derived_from"] = DerivedFromRef(
        project=derived.project,
        repo=derived.repo,
        refreshed_at=_utc_now_iso(),
    )
    # Preserve local posture fields explicitly.
    data["agent_instructions"] = target.agent_instructions
    data["agent_profile"] = target.agent_profile
    data["protected"] = target.protected
    data["name"] = target.name
    return ProjectPath.model_validate(data)


class DerivedSelection(BaseModel):
    """Parsed ``project/repo`` or ``project/repo/component`` selection."""

    model_config = ConfigDict(extra="forbid")

    project: str = Field(..., description="Source workspace project name")
    repo: str = Field(..., description="Source repository name")
    component: Optional[str] = Field(None, description="Optional component name")


def parse_selection(selection: str) -> DerivedSelection | CatalogError:
    """Parse ``project/repo`` or ``project/repo/component`` selection strings."""
    trimmed = selection.strip()
    parts = [part.strip() for part in trimmed.split("/")]
    if len(parts) not in {2, 3} or not all(parts):
        return CatalogError(
            kind="invalid_selection",
            message=f"selection '{selection}' must be project/repo or project/repo/component",
        )
    if len(parts) == 2:
        return DerivedSelection(project=parts[0], repo=parts[1], component=None)
    return DerivedSelection(project=parts[0], repo=parts[1], component=parts[2])


def _record_wanted(
    wanted: dict[tuple[str, str], set[str] | None],
    selection: DerivedSelection,
) -> None:
    """Merge a selection into repo-keyed component allow-lists (None = whole repo)."""
    key = (selection.project, selection.repo)
    if selection.component is None:
        wanted[key] = None
        return
    if key in wanted and wanted[key] is None:
        return
    names = wanted.setdefault(key, set())
    if names is not None:
        names.add(selection.component)


def _neighbor_selections(
    config: MetagitConfig,
    selection: DerivedSelection,
) -> list[DerivedSelection] | CatalogError:
    """Return outbound ``depends_on`` neighbors for a component selection."""
    if selection.component is None:
        return []
    identity = f"{selection.project}/{selection.repo}/{selection.component}"
    result = ComponentGraphService().neighborhood(
        config,
        identity,
        depth=1,
        direction="out",
        types=["depends_on"],
    )
    if isinstance(result, Exception):
        return CatalogError(kind="dependency_lookup_failed", message=str(result))
    if result is None:
        return CatalogError(
            kind="source_not_found",
            message=f"component '{identity}' not found",
        )
    origin_id = str(result["origin"].get("id", ""))
    neighbors: list[DerivedSelection] = []
    for node in result["nodes"]:
        if str(node.get("id", "")) == origin_id:
            continue
        project = str(node.get("project", "")).strip()
        repo = str(node.get("repo", "")).strip()
        name = str(node.get("name", "")).strip()
        if not project or not repo or not name:
            continue
        neighbors.append(DerivedSelection(project=project, repo=repo, component=name))
    return neighbors


def _scope_component_names(
    project: WorkspaceProject,
    source_project: str,
    source_repo: str,
) -> list[str] | None:
    """Return the derived allow-list for a source repo, or None for the whole repo."""
    if project.derived is None:
        return None
    for scope in project.derived.sources:
        if scope.project != source_project:
            continue
        if scope.repos and source_repo not in scope.repos:
            continue
        return list(scope.components) if scope.components else None
    return None


class DerivedProjectService:
    """Manage derived projects that surgically subset other projects in-manifest."""

    def create(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        name: str,
        selections: list[str],
        description: Optional[str] = None,
        agent_instructions: Optional[str] = None,
        enable_dedupe: bool = True,
        force: bool = False,
        include_dependencies: bool = False,
    ) -> DerivedMutationResult:
        """Create a derived project from ``project/repo`` or ``project/repo/component`` selections."""
        _ = force
        trimmed = name.strip()
        if not trimmed:
            return self._error("create", "invalid_name", "project name is required")
        name_err = validate_layout_name(
            trimmed,
            label="project name",
            reserved=reserved_project_names(),
        )
        if name_err:
            return self._error("create", "invalid_name", name_err, project_name=trimmed)
        if not config.workspace:
            config.workspace = Workspace(projects=[])
        if find_project(config, trimmed) is not None:
            return self._error(
                "create",
                "already_exists",
                f"project '{trimmed}' already exists",
                project_name=trimmed,
            )
        if not selections:
            return self._error(
                "create",
                "empty_selection",
                "at least one project/repo selection is required",
                project_name=trimmed,
            )

        parsed_selections: list[DerivedSelection] = []
        for raw in selections:
            parsed = parse_selection(raw)
            if isinstance(parsed, CatalogError):
                return self._error("create", parsed.kind, parsed.message, project_name=trimmed)
            parsed_selections.append(parsed)

        if include_dependencies:
            extras: list[DerivedSelection] = []
            for parsed in parsed_selections:
                if parsed.component is None:
                    continue
                neighbors = _neighbor_selections(config, parsed)
                if isinstance(neighbors, CatalogError):
                    return self._error("create", neighbors.kind, neighbors.message, project_name=trimmed)
                extras.extend(neighbors)
            parsed_selections.extend(extras)

        wanted: dict[tuple[str, str], set[str] | None] = {}
        ordered_keys: list[tuple[str, str]] = []
        for parsed in parsed_selections:
            key = (parsed.project, parsed.repo)
            if key not in ordered_keys:
                ordered_keys.append(key)
            _record_wanted(wanted, parsed)

        copied: list[ProjectPath] = []
        for source_project_name, source_repo_name in ordered_keys:
            source_project = find_project(config, source_project_name)
            if source_project is None:
                return self._error(
                    "create",
                    "source_not_found",
                    f"source project '{source_project_name}' not found",
                    project_name=trimmed,
                )
            source_repo = find_repo(source_project, source_repo_name)
            if source_repo is None:
                return self._error(
                    "create",
                    "source_not_found",
                    f"source repo '{source_project_name}/{source_repo_name}' not found",
                    project_name=trimmed,
                )
            component_names = wanted[(source_project_name, source_repo_name)]
            if component_names is not None:
                missing = sorted(
                    name for name in component_names if not any(item.name == name for item in source_repo.components)
                )
                if missing:
                    return self._error(
                        "create",
                        "source_not_found",
                        (f"source component '{source_project_name}/{source_repo_name}/{missing[0]}' not found"),
                        project_name=trimmed,
                    )
            if any(item.name == source_repo_name for item in copied):
                return self._error(
                    "create",
                    "duplicate_repo_name",
                    f"duplicate derived repo name '{source_repo_name}' in selection",
                    project_name=trimmed,
                )
            derived_repo = _copy_identity_from_source(
                source_repo,
                name=source_repo_name,
                derived_from=DerivedFromRef(
                    project=source_project_name,
                    repo=source_repo_name,
                    refreshed_at=_utc_now_iso(),
                ),
                component_names=None if component_names is None else sorted(component_names),
            )
            copied.append(derived_repo)

        derived_project = WorkspaceProject(
            name=trimmed,
            description=description,
            agent_instructions=agent_instructions,
            dedupe=ProjectDedupeOverride(enabled=True) if enable_dedupe else None,
            derived=DerivedProjectConfig(
                enabled=True,
                sources=self._sources_from_wanted(wanted),
            ),
            repos=copied,
        )
        if not enable_dedupe:
            for candidate in copied:
                duplicates = find_duplicate_identities(config, candidate)
                if duplicates:
                    locations = ", ".join(f"{proj}/{repo}" for proj, repo in duplicates)
                    return self._error(
                        "create",
                        "duplicate_identity",
                        (f"repo identity already registered as {locations}; enable dedupe or choose different repos"),
                        project_name=trimmed,
                    )

        config.workspace.projects.append(derived_project)
        save_err = self._save(config=config, config_path=config_path)
        if save_err:
            return self._error(
                "create",
                "save_failed",
                str(save_err),
                project_name=trimmed,
            )
        return DerivedMutationResult(
            ok=True,
            operation="create",
            project_name=trimmed,
            repo_names=[repo.name for repo in copied],
            config_path=config_path,
            data={
                "derived": derived_project.derived.model_dump(mode="json") if derived_project.derived else None,
                "dedupe_enabled": enable_dedupe,
            },
        )

    def refresh(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        project_name: str,
        repo_names: Optional[list[str]] = None,
        force: bool = False,
    ) -> DerivedMutationResult:
        """Re-pull identity fields from source without changing membership."""
        project = find_project(config, project_name)
        if project is None:
            return self._error(
                "refresh",
                "project_not_found",
                f"project '{project_name}' not found",
                project_name=project_name,
            )
        if project.derived is None or not project.derived.enabled:
            return self._error(
                "refresh",
                "not_derived",
                f"project '{project_name}' is not a derived project",
                project_name=project_name,
            )
        if project_is_protected(project) and not force:
            return self._error(
                "refresh",
                "protected",
                f"project '{project_name}' is protected (use force=True)",
                project_name=project_name,
            )

        wanted = set(repo_names) if repo_names else None
        refreshed: list[str] = []
        updated: list[ProjectPath] = []
        for repo in project.repos:
            if wanted is not None and repo.name not in wanted:
                updated.append(repo)
                continue
            if repo.derived_from is None:
                return self._error(
                    "refresh",
                    "missing_provenance",
                    f"repo '{repo.name}' lacks derived_from",
                    project_name=project_name,
                )
            source_project = find_project(config, repo.derived_from.project)
            if source_project is None:
                return self._error(
                    "refresh",
                    "source_not_found",
                    (f"source project '{repo.derived_from.project}' missing for derived repo '{repo.name}'"),
                    project_name=project_name,
                )
            source_repo = find_repo(source_project, repo.derived_from.repo)
            if source_repo is None:
                return self._error(
                    "refresh",
                    "source_not_found",
                    (
                        f"source repo '{repo.derived_from.project}/"
                        f"{repo.derived_from.repo}' missing for derived repo '{repo.name}'"
                    ),
                    project_name=project_name,
                )
            allow = _scope_component_names(project, repo.derived_from.project, repo.derived_from.repo)
            updated.append(_refresh_identity(repo, source_repo, allow))
            refreshed.append(repo.name)

        if wanted is not None:
            present = {repo.name for repo in project.repos}
            missing = sorted(wanted - present)
            if missing:
                return self._error(
                    "refresh",
                    "repo_not_found",
                    f"repos not in derived project: {', '.join(missing)}",
                    project_name=project_name,
                )

        project.repos = updated
        save_err = self._save(config=config, config_path=config_path)
        if save_err:
            return self._error(
                "refresh",
                "save_failed",
                str(save_err),
                project_name=project_name,
            )
        return DerivedMutationResult(
            ok=True,
            operation="refresh",
            project_name=project_name,
            repo_names=refreshed,
            config_path=config_path,
        )

    def include(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        project_name: str,
        selection: str,
        force: bool = False,
    ) -> DerivedMutationResult:
        """Add one source repo, or merge a component into an existing derived repo."""
        project = find_project(config, project_name)
        if project is None:
            return self._error(
                "include",
                "project_not_found",
                f"project '{project_name}' not found",
                project_name=project_name,
            )
        if project.derived is None or not project.derived.enabled:
            return self._error(
                "include",
                "not_derived",
                f"project '{project_name}' is not a derived project",
                project_name=project_name,
            )
        if project_is_protected(project) and not force:
            return self._error(
                "include",
                "protected",
                f"project '{project_name}' is protected (use force=True)",
                project_name=project_name,
            )
        parsed = parse_selection(selection)
        if isinstance(parsed, CatalogError):
            return self._error("include", parsed.kind, parsed.message, project_name=project_name)
        source_project_name, source_repo_name = parsed.project, parsed.repo
        source_project = find_project(config, source_project_name)
        if source_project is None:
            return self._error(
                "include",
                "source_not_found",
                f"source project '{source_project_name}' not found",
                project_name=project_name,
            )
        source_repo = find_repo(source_project, source_repo_name)
        if source_repo is None:
            return self._error(
                "include",
                "source_not_found",
                f"source repo '{source_project_name}/{source_repo_name}' not found",
                project_name=project_name,
            )
        if parsed.component is not None and not any(item.name == parsed.component for item in source_repo.components):
            return self._error(
                "include",
                "source_not_found",
                f"source component '{source_project_name}/{source_repo_name}/{parsed.component}' not found",
                project_name=project_name,
            )
        existing = find_repo(project, source_repo_name)
        if existing is not None:
            if not self._merge_into_existing_repo(project, existing, source_repo, parsed):
                return DerivedMutationResult(
                    ok=True,
                    operation="noop",
                    project_name=project_name,
                    repo_names=[source_repo_name],
                    config_path=config_path,
                )
        else:
            component_names = None if parsed.component is None else [parsed.component]
            derived_repo = _copy_identity_from_source(
                source_repo,
                name=source_repo_name,
                derived_from=DerivedFromRef(
                    project=source_project_name,
                    repo=source_repo_name,
                    refreshed_at=_utc_now_iso(),
                ),
                component_names=component_names,
            )
            project.repos.append(derived_repo)
            self._upsert_source_scope(
                project,
                source_project_name,
                source_repo_name,
                components=component_names or [],
            )
        save_err = self._save(config=config, config_path=config_path)
        if save_err:
            return self._error(
                "include",
                "save_failed",
                str(save_err),
                project_name=project_name,
            )
        return DerivedMutationResult(
            ok=True,
            operation="include",
            project_name=project_name,
            repo_names=[source_repo_name],
            config_path=config_path,
        )

    def exclude(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        project_name: str,
        repo_name: str,
        force: bool = False,
    ) -> DerivedMutationResult:
        """Remove one repo from a derived project's frozen membership."""
        project = find_project(config, project_name)
        if project is None:
            return self._error(
                "exclude",
                "project_not_found",
                f"project '{project_name}' not found",
                project_name=project_name,
            )
        if project.derived is None or not project.derived.enabled:
            return self._error(
                "exclude",
                "not_derived",
                f"project '{project_name}' is not a derived project",
                project_name=project_name,
            )
        existing = find_repo(project, repo_name)
        if existing is None:
            return self._error(
                "exclude",
                "repo_not_found",
                f"repo '{repo_name}' not found in project '{project_name}'",
                project_name=project_name,
            )
        if repo_is_protected(project, existing) and not force:
            return self._error(
                "exclude",
                "protected",
                f"repo '{repo_name}' or project '{project_name}' is protected (use force=True)",
                project_name=project_name,
            )
        project.repos = [repo for repo in project.repos if repo.name != repo_name]
        if existing.derived_from is not None:
            self._remove_source_scope_repo(
                project,
                existing.derived_from.project,
                existing.derived_from.repo,
            )
        save_err = self._save(config=config, config_path=config_path)
        if save_err:
            return self._error(
                "exclude",
                "save_failed",
                str(save_err),
                project_name=project_name,
            )
        return DerivedMutationResult(
            ok=True,
            operation="exclude",
            project_name=project_name,
            repo_names=[repo_name],
            config_path=config_path,
        )

    def _merge_into_existing_repo(
        self,
        project: WorkspaceProject,
        existing: ProjectPath,
        source_repo: ProjectPath,
        parsed: DerivedSelection,
    ) -> bool:
        """Merge a selection into an existing derived repo. True when membership changed."""
        allow = _scope_component_names(project, parsed.project, parsed.repo)
        if parsed.component is None:
            have = {item.name for item in existing.components}
            source_names = {item.name for item in source_repo.components}
            if allow is None and have >= source_names:
                return False
            existing.components = _copy_components(source_repo, None)
            self._widen_source_scope(project, parsed.project, parsed.repo)
            return True
        already = any(item.name == parsed.component for item in existing.components)
        changed = False
        if not already:
            source_comp = next(item for item in source_repo.components if item.name == parsed.component)
            existing.components.append(source_comp.model_copy(deep=True))
            changed = True
        if allow is not None and parsed.component not in allow:
            self._upsert_source_scope(
                project,
                parsed.project,
                parsed.repo,
                components=[parsed.component],
            )
            changed = True
        return changed

    def _widen_source_scope(
        self,
        project: WorkspaceProject,
        source_project: str,
        source_repo: str,
    ) -> None:
        """Clear a source allow-list so the derived repo tracks the whole source repo."""
        if project.derived is None:
            project.derived = DerivedProjectConfig(enabled=True, sources=[])
        for scope in project.derived.sources:
            if scope.project != source_project:
                continue
            if source_repo in scope.repos:
                scope.components = []
                return
        project.derived.sources.append(DerivedSourceScope(project=source_project, repos=[source_repo], components=[]))

    def _sources_from_wanted(
        self,
        wanted: dict[tuple[str, str], set[str] | None],
    ) -> list[DerivedSourceScope]:
        """Build derived.sources from repo-keyed component allow-lists."""
        grouped: dict[str, list[tuple[str, set[str] | None]]] = {}
        for (project_name, repo_name), names in wanted.items():
            grouped.setdefault(project_name, []).append((repo_name, names))
        sources: list[DerivedSourceScope] = []
        for project_name in sorted(grouped):
            items = grouped[project_name]
            filters = {frozenset(names) if names is not None else None for _, names in items}
            if len(filters) == 1:
                names = items[0][1]
                sources.append(
                    DerivedSourceScope(
                        project=project_name,
                        repos=sorted(repo for repo, _ in items),
                        components=sorted(names) if names else [],
                    )
                )
                continue
            for repo_name, names in sorted(items):
                sources.append(
                    DerivedSourceScope(
                        project=project_name,
                        repos=[repo_name],
                        components=sorted(names) if names else [],
                    )
                )
        return sources

    def _upsert_source_scope(
        self,
        project: WorkspaceProject,
        source_project: str,
        source_repo: str,
        components: Optional[list[str]] = None,
    ) -> None:
        """Record include intent on derived.sources."""
        if project.derived is None:
            project.derived = DerivedProjectConfig(enabled=True, sources=[])
        allow = list(components or [])
        for scope in project.derived.sources:
            if scope.project != source_project:
                continue
            if source_repo in scope.repos:
                for name in allow:
                    if name not in scope.components:
                        scope.components.append(name)
                scope.components.sort()
                return
            if not allow and not scope.components:
                scope.repos.append(source_repo)
                scope.repos.sort()
                return
        project.derived.sources.append(
            DerivedSourceScope(project=source_project, repos=[source_repo], components=allow)
        )

    def _remove_source_scope_repo(
        self,
        project: WorkspaceProject,
        source_project: str,
        source_repo: str,
    ) -> None:
        """Drop a repo from derived.sources intent when excluded."""
        if project.derived is None:
            return
        remaining: list[DerivedSourceScope] = []
        for scope in project.derived.sources:
            if scope.project != source_project:
                remaining.append(scope)
                continue
            repos = [name for name in scope.repos if name != source_repo]
            if repos:
                remaining.append(
                    DerivedSourceScope(
                        project=source_project,
                        repos=repos,
                        components=list(scope.components),
                    )
                )
        project.derived.sources = remaining

    def _save(self, *, config: MetagitConfig, config_path: str) -> Exception | None:
        """Persist the manifest."""
        manager = MetagitConfigManager(config_path)
        result = manager.save_config(config)
        return result if isinstance(result, Exception) else None

    def _error(
        self,
        operation: str,
        kind: str,
        message: str,
        *,
        project_name: str = "",
    ) -> DerivedMutationResult:
        """Build a failed mutation result."""
        return DerivedMutationResult(
            ok=False,
            error=CatalogError(kind=kind, message=message),
            operation=operation,
            project_name=project_name,
        )
