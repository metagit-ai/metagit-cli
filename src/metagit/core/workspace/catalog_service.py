#!/usr/bin/env python
"""
List and mutate workspace projects and repositories in `.metagit.yml`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.catalog_models import (
    CatalogError,
    CatalogMutationResult,
    CatalogResult,
    ProjectListEntry,
    RepoListEntry,
    WorkspaceSummary,
)
from metagit.core.workspace.layout_resolver import validate_layout_name
from metagit.core.workspace.models import Workspace, WorkspaceProject
from metagit.core.workspace.protection import project_is_protected, repo_is_protected
from metagit.core.workspace.root_resolver import reserved_project_names, resolve_definition_root
from metagit.core.workspace.workspace_dedupe import find_duplicate_identities


def _repo_ensure_conflict(
    existing: ProjectPath,
    desired: ProjectPath,
) -> str | None:
    """Return a conflict message when ``desired`` disagrees with ``existing``."""
    if desired.url is not None:
        existing_url = str(existing.url) if existing.url else None
        desired_url = str(desired.url)
        if existing_url != desired_url:
            return f"url mismatch for repo '{existing.name}': catalog has {existing_url!r}, requested {desired_url!r}"
    if desired.path is not None and existing.path != desired.path:
        return f"path mismatch for repo '{existing.name}': catalog has {existing.path!r}, requested {desired.path!r}"
    return None


def _project_ensure_conflict(
    existing: WorkspaceProject,
    *,
    description: str | None,
    agent_instructions: str | None,
    protected: bool | None = None,
    tags: dict[str, str] | None = None,
) -> str | None:
    """Return a conflict message when optional project fields disagree."""
    if description is not None and existing.description != description:
        return (
            f"description mismatch for project '{existing.name}': "
            f"catalog has {existing.description!r}, requested {description!r}"
        )
    if agent_instructions is not None and existing.agent_instructions != agent_instructions:
        return f"agent_instructions mismatch for project '{existing.name}'"
    if protected is not None and bool(existing.protected) != protected:
        return f"protected mismatch for project '{existing.name}'"
    if tags is not None and dict(existing.tags) != tags:
        return f"tags mismatch for project '{existing.name}'"
    return None


class WorkspaceCatalogService:
    """CRUD-style catalog operations for workspace manifests."""

    def __init__(
        self,
        index_service: Optional[WorkspaceIndexService] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()

    def list_workspace(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        *,
        include_index: bool = True,
    ) -> CatalogResult:
        """Return workspace summary, projects, and optional index rows."""
        summary = self._workspace_summary(
            config=config,
            config_path=config_path,
            workspace_root=workspace_root,
        )
        projects = self.list_projects(config=config).data or {}
        payload: dict[str, Any] = {
            "summary": summary.model_dump(mode="json"),
            "projects": projects.get("projects", []),
        }
        if include_index:
            payload["repos_index"] = self._index.build_index(
                config=config,
                workspace_root=workspace_root,
                definition_root=resolve_definition_root(config_path),
            )
        return CatalogResult(ok=True, data=payload)

    def list_projects(self, config: MetagitConfig) -> CatalogResult:
        """List workspace projects defined in the manifest."""
        if not config.workspace:
            return CatalogResult(
                ok=True,
                data={"projects": [], "project_count": 0},
            )
        entries = [
            ProjectListEntry(
                name=project.name,
                description=project.description,
                agent_instructions=project.agent_instructions,
                protected=bool(project.protected),
                tags=dict(project.tags),
                metadata=dict(project.metadata),
                documentation_count=len(project.documentation or []),
                dedupe_enabled=(project.dedupe.enabled if project.dedupe is not None else None),
                derived=bool(project.derived is not None and project.derived.enabled),
                repo_count=len(project.repos),
            ).model_dump(mode="json")
            for project in config.workspace.projects
        ]
        return CatalogResult(
            ok=True,
            data={"projects": entries, "project_count": len(entries)},
        )

    def list_repos(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        project_name: Optional[str] = None,
        include_status: bool = True,
    ) -> CatalogResult:
        """List configured repositories, optionally scoped to one project."""
        if not config.workspace:
            return CatalogResult(ok=True, data={"repos": [], "repo_count": 0})
        index_rows: list[dict[str, Any]] = []
        if include_status:
            index_rows = self._index.build_index(
                config=config,
                workspace_root=workspace_root,
            )
        index_by_key = {(row["project_name"], row["repo_name"]): row for row in index_rows}
        repos: list[dict[str, Any]] = []
        for project in config.workspace.projects:
            if project_name and project.name != project_name:
                continue
            for repo in project.repos:
                row = index_by_key.get((project.name, repo.name), {})
                entry = RepoListEntry(
                    project_name=project.name,
                    repo=repo,
                    configured_path=repo.path,
                    repo_path=row.get("repo_path"),
                    exists=row.get("exists"),
                    status=row.get("status"),
                )
                repos.append(entry.model_dump(mode="json"))
        return CatalogResult(
            ok=True,
            data={"repos": repos, "repo_count": len(repos)},
        )

    def add_project(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        name: str,
        description: Optional[str] = None,
        agent_instructions: Optional[str] = None,
        protected: Optional[bool] = None,
        tags: Optional[dict[str, str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        ensure: bool = False,
        force: bool = False,
    ) -> CatalogMutationResult:
        """Add a workspace project (group) to the manifest."""
        _ = force
        trimmed = name.strip()
        if not trimmed:
            return self._mutation_error(
                entity="project",
                operation="add",
                kind="invalid_name",
                message="project name is required",
            )

        name_err = validate_layout_name(
            trimmed,
            label="project name",
            reserved=reserved_project_names(),
        )
        if name_err:
            return self._mutation_error(
                entity="project",
                operation="add",
                kind="invalid_name",
                message=name_err,
                project_name=trimmed,
            )
        if not config.workspace:
            config.workspace = Workspace(projects=[])
        for project in config.workspace.projects:
            if project.name == trimmed:
                if not ensure:
                    return self._mutation_error(
                        entity="project",
                        operation="add",
                        kind="already_exists",
                        message=f"project '{trimmed}' already exists",
                        project_name=trimmed,
                    )
                conflict = _project_ensure_conflict(
                    project,
                    description=description,
                    agent_instructions=agent_instructions,
                    protected=protected,
                    tags=tags,
                )
                if conflict:
                    return self._mutation_error(
                        entity="project",
                        operation="add",
                        kind="conflict",
                        message=conflict,
                        project_name=trimmed,
                    )
                return CatalogMutationResult(
                    ok=True,
                    entity="project",
                    operation="noop",
                    project_name=trimmed,
                    config_path=config_path,
                )
        config.workspace.projects.append(
            WorkspaceProject(
                name=trimmed,
                description=description,
                agent_instructions=agent_instructions,
                protected=protected if protected is not None else False,
                tags=tags or {},
                metadata=metadata or {},
                repos=[],
            )
        )
        save_err = self._save(config=config, config_path=config_path)
        if save_err:
            return self._mutation_error(
                entity="project",
                operation="add",
                kind="save_failed",
                message=str(save_err),
                project_name=trimmed,
            )
        return CatalogMutationResult(
            ok=True,
            entity="project",
            operation="add",
            project_name=trimmed,
            config_path=config_path,
        )

    def remove_project(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        name: str,
        force: bool = False,
    ) -> CatalogMutationResult:
        """Remove a workspace project from the manifest (repos are removed with it)."""
        trimmed = name.strip()
        if not config.workspace:
            return self._mutation_error(
                entity="project",
                operation="remove",
                kind="not_found",
                message=f"project '{trimmed}' not found",
                project_name=trimmed,
            )
        target = self._find_project(config=config, project_name=trimmed)
        if target is None:
            return self._mutation_error(
                entity="project",
                operation="remove",
                kind="not_found",
                message=f"project '{trimmed}' not found",
                project_name=trimmed,
            )
        if project_is_protected(target) and not force:
            return self._mutation_error(
                entity="project",
                operation="remove",
                kind="protected",
                message=f"project '{trimmed}' is protected (use force=True)",
                project_name=trimmed,
            )
        before = len(config.workspace.projects)
        config.workspace.projects = [project for project in config.workspace.projects if project.name != trimmed]
        if len(config.workspace.projects) == before:
            return self._mutation_error(
                entity="project",
                operation="remove",
                kind="not_found",
                message=f"project '{trimmed}' not found",
                project_name=trimmed,
            )
        save_err = self._save(config=config, config_path=config_path)
        if save_err:
            return self._mutation_error(
                entity="project",
                operation="remove",
                kind="save_failed",
                message=str(save_err),
                project_name=trimmed,
            )
        return CatalogMutationResult(
            ok=True,
            entity="project",
            operation="remove",
            project_name=trimmed,
            config_path=config_path,
        )

    def add_repo(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        project_name: str,
        repo: ProjectPath,
        ensure: bool = False,
        force: bool = False,
    ) -> CatalogMutationResult:
        """Add a repository entry under a workspace project."""
        project = self._find_project(config=config, project_name=project_name)
        if project is None:
            return self._mutation_error(
                entity="repo",
                operation="add",
                kind="project_not_found",
                message=f"project '{project_name}' not found",
                project_name=project_name,
            )
        if project_is_protected(project) and not force:
            return self._mutation_error(
                entity="repo",
                operation="add",
                kind="protected",
                message=(f"project '{project_name}' is protected (use force=True to add repos)"),
                project_name=project_name,
                repo_name=repo.name,
            )
        for existing in project.repos:
            if existing.name == repo.name:
                if not ensure:
                    return self._mutation_error(
                        entity="repo",
                        operation="add",
                        kind="already_exists",
                        message=(f"repo '{repo.name}' already exists in project '{project_name}'"),
                        project_name=project_name,
                        repo_name=repo.name,
                    )
                conflict = _repo_ensure_conflict(existing, repo)
                if conflict:
                    return self._mutation_error(
                        entity="repo",
                        operation="add",
                        kind="conflict",
                        message=conflict,
                        project_name=project_name,
                        repo_name=repo.name,
                    )
                return CatalogMutationResult(
                    ok=True,
                    entity="repo",
                    operation="noop",
                    project_name=project_name,
                    repo_name=repo.name,
                    config_path=config_path,
                )
        if repo.path is None and repo.url is None:
            return self._mutation_error(
                entity="repo",
                operation="add",
                kind="invalid_repo",
                message="repo requires at least path or url",
                project_name=project_name,
                repo_name=repo.name,
            )
        duplicates = find_duplicate_identities(config, repo)
        if duplicates:
            locations = ", ".join(f"{proj}/{name}" for proj, name in duplicates)
            return self._mutation_error(
                entity="repo",
                operation="add",
                kind="duplicate_identity",
                message=(
                    f"repo identity already registered as {locations}; "
                    "reuse that entry or enable workspace dedupe before adding again"
                ),
                project_name=project_name,
                repo_name=repo.name,
            )
        project.repos.append(repo)
        save_err = self._save(config=config, config_path=config_path)
        if save_err:
            return self._mutation_error(
                entity="repo",
                operation="add",
                kind="save_failed",
                message=str(save_err),
                project_name=project_name,
                repo_name=repo.name,
            )
        return CatalogMutationResult(
            ok=True,
            entity="repo",
            operation="add",
            project_name=project_name,
            repo_name=repo.name,
            config_path=config_path,
        )

    def remove_repo(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        project_name: str,
        repo_name: str,
        force: bool = False,
    ) -> CatalogMutationResult:
        """Remove a repository entry from a workspace project (manifest only)."""
        project = self._find_project(config=config, project_name=project_name)
        if project is None:
            return self._mutation_error(
                entity="repo",
                operation="remove",
                kind="project_not_found",
                message=f"project '{project_name}' not found",
                project_name=project_name,
                repo_name=repo_name,
            )
        existing_repo = next(
            (item for item in project.repos if item.name == repo_name),
            None,
        )
        if existing_repo is not None and repo_is_protected(project, existing_repo) and not force:
            return self._mutation_error(
                entity="repo",
                operation="remove",
                kind="protected",
                message=(f"repo '{repo_name}' or project '{project_name}' is protected (use force=True)"),
                project_name=project_name,
                repo_name=repo_name,
            )
        before = len(project.repos)
        project.repos = [item for item in project.repos if item.name != repo_name]
        if len(project.repos) == before:
            return self._mutation_error(
                entity="repo",
                operation="remove",
                kind="not_found",
                message=(f"repo '{repo_name}' not found in project '{project_name}'"),
                project_name=project_name,
                repo_name=repo_name,
            )
        save_err = self._save(config=config, config_path=config_path)
        if save_err:
            return self._mutation_error(
                entity="repo",
                operation="remove",
                kind="save_failed",
                message=str(save_err),
                project_name=project_name,
                repo_name=repo_name,
            )
        return CatalogMutationResult(
            ok=True,
            entity="repo",
            operation="remove",
            project_name=project_name,
            repo_name=repo_name,
            config_path=config_path,
        )

    def build_repo_from_fields(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        path: Optional[str] = None,
        url: Optional[str] = None,
        sync: Optional[bool] = None,
        agent_instructions: Optional[str] = None,
        tags: Optional[dict[str, str]] = None,
        protected: Optional[bool] = None,
    ) -> ProjectPath | CatalogError:
        """Construct a ProjectPath from API/MCP/CLI fields."""
        trimmed_name = name.strip()
        if not trimmed_name:
            return CatalogError(kind="invalid_name", message="repo name is required")
        return ProjectPath(
            name=trimmed_name,
            description=description,
            path=path,
            url=url,
            sync=sync,
            agent_instructions=agent_instructions,
            tags=tags or {},
            protected=protected if protected is not None else False,
        )

    def _workspace_summary(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
    ) -> WorkspaceSummary:
        project_count = len(config.workspace.projects) if config.workspace else 0
        repo_count = 0
        if config.workspace:
            repo_count = sum(len(project.repos) for project in config.workspace.projects)
        return WorkspaceSummary(
            definition_path=str(Path(config_path).resolve()),
            workspace_root=str(Path(workspace_root).resolve()),
            file_name=config.name,
            file_description=config.description,
            file_agent_instructions=config.agent_instructions,
            workspace=config.workspace,
            project_count=project_count,
            repo_count=repo_count,
        )

    def _find_project(self, config: MetagitConfig, project_name: str) -> Optional[WorkspaceProject]:
        if not config.workspace:
            return None
        for project in config.workspace.projects:
            if project.name == project_name:
                return project
        return None

    def _save(self, config: MetagitConfig, config_path: str) -> Optional[Exception]:
        manager = MetagitConfigManager(metagit_config=config)
        result = manager.save_config(config, Path(config_path))
        if isinstance(result, Exception):
            return result
        return None

    def _mutation_error(
        self,
        *,
        entity: str,
        operation: str,
        kind: str,
        message: str,
        project_name: str = "",
        repo_name: Optional[str] = None,
    ) -> CatalogMutationResult:
        return CatalogMutationResult(
            ok=False,
            error=CatalogError(kind=kind, message=message),
            entity="repo" if entity == "repo" else "project",
            operation=operation if operation in {"add", "remove", "noop"} else "add",
            project_name=project_name,
            repo_name=repo_name,
            config_path="",
        )
