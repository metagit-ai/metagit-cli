#!/usr/bin/env python
"""Create and maintain derived workspace projects within one umbrella manifest."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

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


def _copy_identity_from_source(
    source: ProjectPath,
    *,
    name: str,
    derived_from: DerivedFromRef,
    local_tags: Optional[dict[str, str]] = None,
    agent_instructions: Optional[str] = None,
    agent_profile: Optional[object] = None,
    protected: Optional[bool] = None,
) -> ProjectPath:
    """Build a derived ProjectPath from a source entry."""
    payload: dict[str, object] = {"name": name}
    for field in _IDENTITY_FIELDS:
        payload[field] = getattr(source, field)
    payload["tags"] = _merge_tags(dict(source.tags), dict(local_tags or {}))
    payload["derived_from"] = derived_from
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


def _refresh_identity(target: ProjectPath, source: ProjectPath) -> ProjectPath:
    """Re-pull identity fields from source while preserving local membership/posture."""
    data = target.model_dump(mode="python")
    for field in _IDENTITY_FIELDS:
        data[field] = getattr(source, field)
    data["tags"] = _merge_tags(dict(source.tags), dict(target.tags))
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


def parse_selection(selection: str) -> tuple[str, str] | CatalogError:
    """Parse ``project/repo`` selection strings."""
    trimmed = selection.strip()
    if "/" not in trimmed:
        return CatalogError(
            kind="invalid_selection",
            message=f"selection '{selection}' must be project/repo",
        )
    project_name, repo_name = trimmed.split("/", 1)
    project_name = project_name.strip()
    repo_name = repo_name.strip()
    if not project_name or not repo_name:
        return CatalogError(
            kind="invalid_selection",
            message=f"selection '{selection}' must be project/repo",
        )
    return project_name, repo_name


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
    ) -> DerivedMutationResult:
        """Create a derived project from ``project/repo`` selections."""
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

        copied: list[ProjectPath] = []
        source_scopes: dict[str, set[str]] = {}
        for raw in selections:
            parsed = parse_selection(raw)
            if isinstance(parsed, CatalogError):
                return self._error("create", parsed.kind, parsed.message, project_name=trimmed)
            source_project_name, source_repo_name = parsed
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
            )
            copied.append(derived_repo)
            source_scopes.setdefault(source_project_name, set()).add(source_repo_name)

        derived_project = WorkspaceProject(
            name=trimmed,
            description=description,
            agent_instructions=agent_instructions,
            dedupe=ProjectDedupeOverride(enabled=True) if enable_dedupe else None,
            derived=DerivedProjectConfig(
                enabled=True,
                sources=[
                    DerivedSourceScope(project=proj, repos=sorted(repos))
                    for proj, repos in sorted(source_scopes.items())
                ],
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
            updated.append(_refresh_identity(repo, source_repo))
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
        """Add one source repo to a derived project's frozen membership."""
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
        source_project_name, source_repo_name = parsed
        if any(repo.name == source_repo_name for repo in project.repos):
            return DerivedMutationResult(
                ok=True,
                operation="noop",
                project_name=project_name,
                repo_names=[source_repo_name],
                config_path=config_path,
            )
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
        derived_repo = _copy_identity_from_source(
            source_repo,
            name=source_repo_name,
            derived_from=DerivedFromRef(
                project=source_project_name,
                repo=source_repo_name,
                refreshed_at=_utc_now_iso(),
            ),
        )
        project.repos.append(derived_repo)
        self._upsert_source_scope(project, source_project_name, source_repo_name)
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

    def _upsert_source_scope(
        self,
        project: WorkspaceProject,
        source_project: str,
        source_repo: str,
    ) -> None:
        """Record include intent on derived.sources."""
        if project.derived is None:
            project.derived = DerivedProjectConfig(enabled=True, sources=[])
        for scope in project.derived.sources:
            if scope.project == source_project:
                if source_repo not in scope.repos:
                    scope.repos.append(source_repo)
                    scope.repos.sort()
                return
        project.derived.sources.append(DerivedSourceScope(project=source_project, repos=[source_repo]))

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
                remaining.append(DerivedSourceScope(project=source_project, repos=repos))
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
