#!/usr/bin/env python
"""
Project context switching and environment export for MCP tools.
"""

import os
from typing import Any, Optional

from metagit.core.config.models import MetagitConfig, Variable, VariableKind
from metagit.core.mcp.services.repo_git_stats import inspect_repo_state
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.workspace.agent_instructions import AgentInstructionsResolver
from metagit.core.workspace.context_models import (
    ProjectContextBundle,
    ProjectContextEnv,
    ProjectContextSession,
    ProjectRepoContext,
    validate_env_value,
)
from metagit.core.workspace.models import WorkspaceProject

_INSPECT_LIMIT = 20
_EXPORTABLE_VARIABLE_KINDS = {
    VariableKind.STRING,
    VariableKind.INTEGER,
    VariableKind.BOOLEAN,
}


class ProjectContextService:
    """Switch active workspace project and build agent context bundles."""

    def __init__(
        self,
        index_service: Optional[WorkspaceIndexService] = None,
        instructions_resolver: Optional[AgentInstructionsResolver] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._instructions = instructions_resolver or AgentInstructionsResolver()

    def switch(
        self,
        config: MetagitConfig,
        workspace_root: str,
        project_name: str,
        *,
        setup_env: bool = True,
        restore_session: bool = True,
        save_previous: bool = True,
        primary_repo: Optional[str] = None,
    ) -> ProjectContextBundle:
        """Switch to a workspace project and return a context bundle."""
        project = self._find_project(config=config, project_name=project_name)
        if project is None:
            return ProjectContextBundle(
                ok=False,
                error="project_not_found",
                project_name=project_name,
                workspace_root=workspace_root,
            )

        store = SessionStore(workspace_root=workspace_root)
        prior_meta = store.get_workspace_meta()
        if save_previous and prior_meta.active_project:
            prior_session = store.get_project_session(project_name=prior_meta.active_project)
            store.save_project_session(session=prior_session)

        bundle = self._build_bundle(
            config=config,
            workspace_root=workspace_root,
            project=project,
            project_name=project_name,
            setup_env=setup_env,
            restore_session=restore_session,
            primary_repo=primary_repo,
        )
        store.set_active_project(project_name=project_name)
        return bundle

    def show(
        self,
        config: MetagitConfig,
        workspace_root: str,
        project_name: Optional[str] = None,
    ) -> ProjectContextBundle:
        """Return context for active or named project without changing active project."""
        store = SessionStore(workspace_root=workspace_root)
        meta = store.get_workspace_meta()
        target = project_name or meta.active_project
        if not target:
            return ProjectContextBundle(
                ok=False,
                error="no_active_project",
                workspace_root=workspace_root,
            )
        project = self._find_project(config=config, project_name=target)
        if project is None:
            return ProjectContextBundle(
                ok=False,
                error="project_not_found",
                project_name=target,
                workspace_root=workspace_root,
            )
        return self._build_bundle(
            config=config,
            workspace_root=workspace_root,
            project=project,
            project_name=target,
            setup_env=True,
            restore_session=True,
            primary_repo=None,
        )

    def _build_bundle(
        self,
        config: MetagitConfig,
        workspace_root: str,
        project: WorkspaceProject,
        project_name: str,
        *,
        setup_env: bool,
        restore_session: bool,
        primary_repo: Optional[str],
    ) -> ProjectContextBundle:
        """Build a project context bundle without updating active project."""
        store = SessionStore(workspace_root=workspace_root)
        rows = self._index.build_index(config=config, workspace_root=workspace_root)
        project_rows = [row for row in rows if row["project_name"] == project_name]
        inspect_truncated = len(project_rows) > _INSPECT_LIMIT
        inspect_rows = project_rows[:_INSPECT_LIMIT]

        repo_contexts: list[ProjectRepoContext] = []
        for row in inspect_rows:
            repo_contexts.append(self._build_repo_context(row=row, project=project))

        session_state = ProjectContextSession(restored=False)
        if restore_session:
            saved = store.get_project_session(project_name=project_name)
            session_state = ProjectContextSession(
                restored=True,
                recent_repos=list(saved.recent_repos),
                primary_repo_path=saved.primary_repo_path,
                agent_notes=saved.agent_notes,
            )

        env_bundle = (
            self._build_env(
                config=config,
                workspace_root=workspace_root,
                project_name=project_name,
                repo_paths=[row["repo_path"] for row in project_rows if row.get("exists")],
                session_overrides=store.get_project_session(project_name=project_name).env_overrides
                if restore_session
                else {},
            )
            if setup_env
            else ProjectContextEnv()
        )

        suggested = self._resolve_suggested_cwd(
            project_rows=project_rows,
            session_primary=session_state.primary_repo_path,
            primary_repo=primary_repo,
            recent_repos=session_state.recent_repos,
        )
        focus_repo_entry = None
        focus_repo_name: Optional[str] = None
        if primary_repo:
            focus_row = self._match_repo_target(rows=project_rows, target=primary_repo)
            if focus_row:
                focus_repo_name = str(focus_row.get("repo_name", "")) or None
                focus_repo_entry = self._instructions.find_repo(
                    project,
                    repo_name=focus_repo_name,
                    repo_path=str(focus_row.get("repo_path", "")),
                )
        elif suggested:
            focus_row = self._match_repo_target(rows=project_rows, target=suggested)
            if focus_row:
                focus_repo_name = str(focus_row.get("repo_name", "")) or None
                focus_repo_entry = self._instructions.find_repo(
                    project,
                    repo_name=focus_repo_name,
                    repo_path=suggested,
                )
        instructions = self._instructions.resolve(
            config,
            project=project,
            repo=focus_repo_entry,
        )

        return ProjectContextBundle(
            ok=True,
            project_name=project_name,
            workspace_root=workspace_root,
            project_description=project.description,
            agent_instructions=project.agent_instructions,
            instruction_layers=instructions.layers,
            effective_agent_instructions=instructions.effective,
            focus_repo_name=focus_repo_name,
            repos=repo_contexts,
            env=env_bundle,
            session=session_state,
            suggested_cwd=suggested,
            inspect_truncated=inspect_truncated,
        )

    def list_env_export_keys(
        self,
        config: MetagitConfig,
        workspace_root: str,
        project_name: str,
    ) -> list[str]:
        """Return sorted env export keys for a project without switching context."""
        project = self._find_project(config=config, project_name=project_name)
        if project is None:
            return []
        bundle = self._build_bundle(
            config=config,
            workspace_root=workspace_root,
            project=project,
            project_name=project_name,
            setup_env=True,
            restore_session=False,
            primary_repo=None,
        )
        return sorted(bundle.env.export.keys())

    def update_session(
        self,
        config: MetagitConfig,
        workspace_root: str,
        project_name: str,
        *,
        recent_repos: Optional[list[str]] = None,
        primary_repo_path: Optional[str] = None,
        agent_notes: Optional[str] = None,
        env_overrides: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Persist session fields for a project."""
        if self._find_project(config=config, project_name=project_name) is None:
            return {"ok": False, "error": "project_not_found"}
        store = SessionStore(workspace_root=workspace_root)
        session = store.update_project_session(
            project_name=project_name,
            recent_repos=recent_repos,
            primary_repo_path=primary_repo_path,
            agent_notes=agent_notes,
            env_overrides=env_overrides,
        )
        return {
            "ok": True,
            "project_name": project_name,
            "session": session.model_dump(mode="json"),
        }

    def _find_project(self, config: MetagitConfig, project_name: str) -> Optional[WorkspaceProject]:
        """Locate workspace project by name."""
        if not config.workspace:
            return None
        for project in config.workspace.projects:
            if project.name == project_name:
                return project
        return None

    def _build_repo_context(
        self,
        row: dict[str, Any],
        project: WorkspaceProject,
    ) -> ProjectRepoContext:
        """Build repo context with optional git inspect."""
        exists = bool(row.get("exists"))
        repo_name = str(row.get("repo_name", ""))
        repo_entry = self._instructions.find_repo(
            project,
            repo_name=repo_name,
            repo_path=str(row.get("repo_path", "")),
        )
        branch: Optional[str] = None
        dirty: Optional[bool] = None
        inspect_error: Optional[str] = None
        if exists and row.get("is_git_repo"):
            inspected = inspect_repo_state(repo_path=str(row["repo_path"]))
            if inspected.get("ok"):
                branch = str(inspected["branch"]) if inspected.get("branch") else None
                dirty = bool(inspected["dirty"]) if inspected.get("dirty") is not None else None
            else:
                inspect_error = str(inspected.get("error", "inspect failed"))
        return ProjectRepoContext(
            repo_name=repo_name,
            repo_path=str(row.get("repo_path", "")),
            configured_path=row.get("configured_path"),
            exists=exists,
            branch=branch,
            dirty=dirty,
            tags=dict(row.get("tags") or {}),
            agent_instructions=repo_entry.agent_instructions if repo_entry else None,
            inspect_error=inspect_error,
        )

    def _build_env(
        self,
        config: MetagitConfig,
        workspace_root: str,
        project_name: str,
        repo_paths: list[str],
        session_overrides: dict[str, str],
    ) -> ProjectContextEnv:
        """Build safe environment exports and hints."""
        exports: dict[str, str] = {
            "METAGIT_WORKSPACE_ROOT": workspace_root,
            "METAGIT_PROJECT": project_name,
            "METAGIT_PROJECT_REPOS": ",".join(repo_paths),
        }
        hints: list[str] = []
        for variable in config.variables or []:
            if not isinstance(variable, Variable):
                continue
            if variable.kind not in _EXPORTABLE_VARIABLE_KINDS:
                hints.append(
                    f"Variable {variable.name} ({variable.kind}) is not auto-exported; resolve {variable.ref} manually."
                )
                continue
            try:
                exports[variable.name] = validate_env_value(str(variable.ref))
            except ValueError:
                hints.append(f"Variable {variable.name} was skipped because its ref looks sensitive.")
        for key, value in session_overrides.items():
            exports[key] = value
        return ProjectContextEnv(export=exports, hints=hints)

    def _resolve_suggested_cwd(
        self,
        project_rows: list[dict[str, Any]],
        session_primary: Optional[str],
        primary_repo: Optional[str],
        recent_repos: list[str],
    ) -> Optional[str]:
        """Pick a suggested working directory for agents."""
        if primary_repo:
            match = self._match_repo_target(rows=project_rows, target=primary_repo)
            if match:
                return str(match.get("repo_path"))
        if session_primary and os.path.isdir(session_primary):
            return session_primary
        for recent in recent_repos:
            if os.path.isdir(recent):
                return recent
        for row in project_rows:
            if row.get("exists"):
                return str(row.get("repo_path"))
        return None

    def _match_repo_target(self, rows: list[dict[str, Any]], target: str) -> Optional[dict[str, Any]]:
        """Match repo by name or resolved path."""
        normalized = target.strip()
        for row in rows:
            if row.get("repo_name") == normalized:
                return row
            if str(row.get("repo_path", "")) == normalized:
                return row
            if normalized in str(row.get("repo_path", "")):
                return row
        return None
