#!/usr/bin/env python
"""Compose project switch with pack, prompt, and objective bootstrap."""

from __future__ import annotations

import shlex
from datetime import datetime, timezone
from typing import Literal, Optional, cast

from metagit.core.config.models import MetagitConfig
from metagit.core.context.context_pack_service import ContextPackService
from metagit.core.context.models import ContextSwitchResult
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.mcp.services.project_context import ProjectContextService
from metagit.core.prompt.models import PromptKind
from metagit.core.prompt.service import PromptService, PromptServiceError
from metagit.core.workspace.layout_resolver import find_project, find_repo
from metagit.core.workspace.models import WorkspaceProject

_TAG_ENV_KEYS = {
    "hermes_profile": "METAGIT_HERMES_PROFILE",
    "working_dir": "METAGIT_WORKING_DIR",
    "default_task_namespace": "METAGIT_DEFAULT_TASK_NAMESPACE",
}


def format_shell_exports(env: dict[str, str]) -> str:
    """Render env map as shell-evalable export lines."""
    lines = [f"export {key}={shlex.quote(value)}" for key, value in sorted(env.items())]
    return "\n".join(lines) + ("\n" if lines else "")


class ContextSwitchService:
    """Full bootstrap orchestrator for mid-session project/repo context switch."""

    def __init__(
        self,
        *,
        project_context: Optional[ProjectContextService] = None,
        pack_service: Optional[ContextPackService] = None,
        prompt_service: Optional[PromptService] = None,
    ) -> None:
        self._project_context = project_context or ProjectContextService()
        self._pack = pack_service or ContextPackService()
        self._prompt = prompt_service or PromptService()

    def switch(
        self,
        *,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        session_root: str,
        definition_root: str,
        project_name: str,
        repo_name: Optional[str] = None,
        tier: Literal[0, 1, 2] = 2,
        include_pack: bool = True,
        include_prompt: bool = True,
        include_objective: bool = True,
        prompt_kind: PromptKind = "context-switch",
        max_tokens: Optional[int] = None,
    ) -> ContextSwitchResult:
        """Switch project context and optionally pack/prompt/objective bootstrap."""
        project = find_project(config, project_name)
        if project is None:
            return ContextSwitchResult(
                ok=False,
                error="project_not_found",
                project_name=project_name,
                repo_name=repo_name,
            )

        if repo_name is not None and find_repo(project, repo_name) is None:
            return ContextSwitchResult(
                ok=False,
                error="repo_not_found",
                project_name=project_name,
                repo_name=repo_name,
            )

        bundle = self._project_context.switch(
            config=config,
            workspace_root=session_root,
            project_name=project_name,
            setup_env=True,
            restore_session=True,
            save_previous=True,
            primary_repo=repo_name,
        )
        if not bundle.ok:
            return ContextSwitchResult(
                ok=False,
                error=bundle.error or "switch_failed",
                project_name=project_name,
                repo_name=repo_name,
                switch=bundle.model_dump(mode="json"),
            )

        warnings: list[str] = []
        pack = None
        if include_pack:
            pack = self._pack.pack(
                config=config,
                config_path=config_path,
                workspace_root=workspace_root,
                session_root=session_root,
                definition_root=definition_root,
                tier=cast(Literal[0, 1, 2], tier),
                project_name=project_name,
                repo_name=repo_name,
                max_tokens=max_tokens,
                active_project=project_name,
            )
            if pack.dropped_sections:
                warnings.append("token budget reached; dropped: " + ", ".join(pack.dropped_sections))

        prompt_text: Optional[str] = None
        emitted_kind: Optional[str] = None
        if include_prompt:
            emitted_kind = prompt_kind
            try:
                prompt_text = self._prompt.emit(
                    config,
                    kind=prompt_kind,
                    scope="workspace",
                    definition_path=config_path,
                    workspace_root=workspace_root,
                    include_instructions=True,
                ).text
            except PromptServiceError as exc:
                warnings.append(f"{prompt_kind} prompt unavailable: {exc}")
                prompt_text = None

        objective_id: Optional[str] = None
        if include_objective:
            objective_id = self._create_objective(
                session_root=session_root,
                project_name=project_name,
                repo_name=repo_name,
                suggested_cwd=bundle.suggested_cwd,
                project_repos_csv=bundle.env.export.get("METAGIT_PROJECT_REPOS", ""),
            )

        env = dict(bundle.env.export)
        env["METAGIT_AGENT_MODE"] = "true"
        self._apply_tag_exports(env, project=project, repo_name=repo_name)
        if "METAGIT_WORKING_DIR" not in env:
            working = bundle.suggested_cwd
            if not working:
                repos_csv = env.get("METAGIT_PROJECT_REPOS", "")
                working = repos_csv.split(",")[0].strip() if repos_csv else None
            if working:
                env["METAGIT_WORKING_DIR"] = working

        return ContextSwitchResult(
            ok=True,
            project_name=project_name,
            repo_name=repo_name,
            switch=bundle.model_dump(mode="json"),
            pack=pack,
            prompt=prompt_text,
            prompt_kind=emitted_kind,
            objective_id=objective_id,
            env=env,
            warnings=warnings,
        )

    def _create_objective(
        self,
        *,
        session_root: str,
        project_name: str,
        repo_name: Optional[str],
        suggested_cwd: Optional[str],
        project_repos_csv: str,
    ) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        objective_id = f"ctx-{stamp}"
        title = f"Context: {project_name}/{repo_name}" if repo_name else f"Context: {project_name}"
        repos: list[str] = []
        if suggested_cwd:
            repos.append(suggested_cwd)
        elif project_repos_csv:
            first = project_repos_csv.split(",")[0].strip()
            if first:
                repos.append(first)
        ObjectiveService(workspace_root=session_root).upsert_partial(
            {
                "id": objective_id,
                "title": title,
                "status": "in_progress",
                "repos": repos,
            }
        )
        return objective_id

    def _apply_tag_exports(
        self,
        env: dict[str, str],
        *,
        project: WorkspaceProject,
        repo_name: Optional[str],
    ) -> None:
        merged: dict[str, str] = dict(project.tags or {})
        if repo_name:
            repo = find_repo(project, repo_name)
            if repo is not None and repo.tags:
                merged.update(repo.tags)
        for tag_key, env_key in _TAG_ENV_KEYS.items():
            value = merged.get(tag_key)
            if value:
                env[env_key] = value
