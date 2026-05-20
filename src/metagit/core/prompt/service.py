#!/usr/bin/env python
"""
Emit metagit prompts for workspace, project, and repo scopes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.prompt.catalog import (
    is_kind_allowed,
    kinds_for_scope,
    list_catalog,
    template_body,
)
from metagit.core.prompt.models import (
    PromptCatalogEntry,
    PromptEmitResult,
    PromptKind,
    PromptScope,
)
from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.workspace.agent_instructions import AgentInstructionsResolver
from metagit.core.workspace.dedupe_resolver import resolve_effective_dedupe
from metagit.core.workspace.models import WorkspaceProject


class PromptServiceError(Exception):
    """Raised when prompt emission cannot proceed."""


class PromptService:
    """Resolve and render prompts for agent consumption."""

    def __init__(self) -> None:
        self._resolver = AgentInstructionsResolver()

    def list_entries(self) -> list[PromptCatalogEntry]:
        """List catalog metadata for all prompt kinds."""
        return list_catalog()

    def emit(
        self,
        config: MetagitConfig,
        *,
        kind: PromptKind,
        scope: PromptScope,
        definition_path: str,
        workspace_root: str,
        project_name: Optional[str] = None,
        repo_name: Optional[str] = None,
        include_instructions: bool = True,
        workspace_dedupe: Optional[WorkspaceDedupeConfig] = None,
    ) -> PromptEmitResult:
        """Emit a prompt for the requested kind and scope."""
        if not is_kind_allowed(kind, scope):
            allowed = ", ".join(kinds_for_scope(scope))
            raise PromptServiceError(
                f"prompt kind {kind!r} is not available for scope {scope!r}; "
                f"allowed: {allowed}"
            )

        project, repo = self._resolve_scope_targets(
            config=config,
            scope=scope,
            project_name=project_name,
            repo_name=repo_name,
        )

        composition = self._resolver.resolve(
            config,
            project=project,
            repo=repo,
        )

        if kind == "instructions":
            text = composition.effective
            if not text:
                raise PromptServiceError(
                    f"no agent_instructions configured for scope {scope!r}"
                )
            return PromptEmitResult(
                kind=kind,
                scope=scope,
                project_name=project.name if project else None,
                repo_name=repo.name if repo else None,
                definition_path=str(Path(definition_path).resolve()),
                instruction_layers=composition.layers,
                text=text,
                metadata=self._metadata(
                    config=config,
                    workspace_root=workspace_root,
                    project=project,
                    repo=repo,
                    workspace_dedupe=workspace_dedupe,
                ),
            )

        body = template_body(
            kind,
            scope,
            project_name=project.name if project else project_name,
            repo_name=repo.name if repo else repo_name,
        )
        sections: list[str] = [body]
        if include_instructions and composition.effective:
            sections.append(
                "---\n\n## Manifest instructions (composed)\n\n" + composition.effective
            )
        return PromptEmitResult(
            kind=kind,
            scope=scope,
            project_name=project.name if project else None,
            repo_name=repo.name if repo else None,
            definition_path=str(Path(definition_path).resolve()),
            instruction_layers=composition.layers if include_instructions else [],
            text="\n\n".join(sections).strip(),
            metadata=self._metadata(
                config=config,
                workspace_root=workspace_root,
                project=project,
                repo=repo,
                workspace_dedupe=workspace_dedupe,
            ),
        )

    def _resolve_scope_targets(
        self,
        *,
        config: MetagitConfig,
        scope: PromptScope,
        project_name: Optional[str],
        repo_name: Optional[str],
    ) -> tuple[Optional[WorkspaceProject], Optional[ProjectPath]]:
        if scope == "workspace":
            if project_name or repo_name:
                raise PromptServiceError(
                    "workspace scope does not accept --project or --repo"
                )
            return None, None

        if not project_name or not project_name.strip():
            raise PromptServiceError("project scope requires --project")
        if not config.workspace:
            raise PromptServiceError("no workspace block in manifest")

        project = next(
            (item for item in config.workspace.projects if item.name == project_name),
            None,
        )
        if project is None:
            raise PromptServiceError(f"project {project_name!r} not found")

        if scope == "project":
            if repo_name:
                raise PromptServiceError("project scope does not accept --repo")
            return project, None

        if not repo_name or not repo_name.strip():
            raise PromptServiceError("repo scope requires --repo")
        repo = self._resolver.find_repo(project, repo_name=repo_name)
        if repo is None:
            raise PromptServiceError(
                f"repo {repo_name!r} not found in project {project_name!r}"
            )
        return project, repo

    def _metadata(
        self,
        *,
        config: MetagitConfig,
        workspace_root: str,
        project: Optional[WorkspaceProject],
        repo: Optional[ProjectPath],
        workspace_dedupe: Optional[WorkspaceDedupeConfig] = None,
    ) -> dict[str, str | int | bool | None]:
        project_count = len(config.workspace.projects) if config.workspace else 0
        repo_count = 0
        if config.workspace:
            repo_count = sum(len(item.repos) for item in config.workspace.projects)
        effective_dedupe: Optional[bool] = None
        project_dedupe_override: Optional[bool] = None
        if workspace_dedupe is not None:
            effective = resolve_effective_dedupe(workspace_dedupe, project)
            effective_dedupe = effective is not None
            if project is not None and project.dedupe is not None:
                project_dedupe_override = project.dedupe.enabled
        return {
            "workspace_root": str(Path(workspace_root).resolve()),
            "file_name": config.name,
            "project_count": project_count,
            "repo_count": repo_count,
            "focused_project": project.name if project else None,
            "focused_repo": repo.name if repo else None,
            "workspace_dedupe_enabled": (
                workspace_dedupe.enabled if workspace_dedupe is not None else None
            ),
            "project_dedupe_override": project_dedupe_override,
            "effective_dedupe_enabled": effective_dedupe,
        }
