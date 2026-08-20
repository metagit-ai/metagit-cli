#!/usr/bin/env python
"""Show, detect, and persist repository CI topology bindings."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.ci_models import CiProvider, CiTargetStatus, RepoCiTarget
from metagit.core.project.ci_target_resolver import CiTargetResolver
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import WorkspaceProject
from metagit.core.workspace.root_resolver import resolve_definition_root, resolve_workspace_root


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_manifest_path(path: str, definition_root: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str((Path(definition_root) / candidate).resolve())


class CiTargetService:
    """Resolve and optionally persist ``ProjectPath.ci`` for managed repos."""

    def __init__(self, *, resolver: Optional[CiTargetResolver] = None) -> None:
        self._resolver = resolver or CiTargetResolver()

    def show(
        self,
        *,
        config: MetagitConfig,
        project_name: str,
        repo_name: str,
        config_path: str,
    ) -> dict[str, Any]:
        located = self._locate(config, project_name, repo_name, config_path)
        if isinstance(located, Exception):
            return {"ok": False, "error": str(located)}
        project, repo, local_path = located
        return {
            "ok": True,
            "project_name": project.name,
            "repo_name": repo.name,
            "repo_path": local_path,
            "url": str(repo.url) if repo.url else None,
            "ci": repo.ci.summary_dict() if repo.ci else None,
        }

    def detect(
        self,
        *,
        config: MetagitConfig,
        project_name: str,
        repo_name: str,
        config_path: str,
        apply: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        located = self._locate(config, project_name, repo_name, config_path)
        if isinstance(located, Exception):
            return {"ok": False, "error": str(located)}
        project, repo, local_path = located
        detected = self._resolver.resolve(
            repo_path=local_path,
            url=str(repo.url) if repo.url else None,
            existing_ci=repo.ci,
            force=force,
        )
        preserved = False
        if detected is None and repo.ci is not None and not force:
            status = repo.ci.status
            status_value = status.value if isinstance(status, CiTargetStatus) else str(status)
            if status_value in {CiTargetStatus.DECLARED.value, CiTargetStatus.OVERRIDDEN.value}:
                detected = repo.ci
                preserved = True
        result: dict[str, Any] = {
            "ok": True,
            "project_name": project.name,
            "repo_name": repo.name,
            "repo_path": local_path,
            "url": str(repo.url) if repo.url else None,
            "ci": detected.summary_dict() if detected else None,
            "preserved": preserved,
            "applied": False,
        }
        if not apply:
            return result
        if detected is None:
            result["ok"] = False
            result["error"] = "No CI topology detected; nothing to apply"
            return result
        updated_repo = repo.model_copy(update={"ci": detected})
        save_error = self._persist_repo(config, config_path, project.name, updated_repo)
        if save_error is not None:
            return {"ok": False, "error": str(save_error)}
        result["applied"] = True
        result["ci"] = detected.summary_dict()
        return result

    def set_target(
        self,
        *,
        config: MetagitConfig,
        project_name: str,
        repo_name: str,
        config_path: str,
        provider: str,
        config_paths: Optional[list[str]] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
        repository: Optional[str] = None,
        definition_ids: Optional[list[Union[str, int]]] = None,
        owner: Optional[str] = None,
        name: Optional[str] = None,
        project_path: Optional[str] = None,
        host: Optional[str] = None,
        status: str = CiTargetStatus.DECLARED.value,
    ) -> dict[str, Any]:
        located = self._locate(config, project_name, repo_name, config_path)
        if isinstance(located, Exception):
            return {"ok": False, "error": str(located)}
        ws_project, repo, local_path = located
        try:
            target = RepoCiTarget(
                provider=CiProvider(provider),
                config_paths=list(config_paths or []),
                host=host,
                organization=organization,
                project=project,
                repository=repository,
                definition_ids=list(definition_ids or []),
                owner=owner,
                name=name,
                project_path=project_path,
                status=CiTargetStatus(status),
                updated_at=_iso_now(),
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        updated_repo = repo.model_copy(update={"ci": target})
        save_error = self._persist_repo(config, config_path, ws_project.name, updated_repo)
        if save_error is not None:
            return {"ok": False, "error": str(save_error)}
        return {
            "ok": True,
            "project_name": ws_project.name,
            "repo_name": repo.name,
            "repo_path": local_path,
            "ci": target.summary_dict(),
            "applied": True,
        }

    def _locate(
        self,
        config: MetagitConfig,
        project_name: str,
        repo_name: str,
        config_path: str,
    ) -> Union[tuple[WorkspaceProject, ProjectPath, Optional[str]], Exception]:
        if not config.workspace or not config.workspace.projects:
            return Exception("No workspace projects found in .metagit.yml")
        project = next(
            (item for item in config.workspace.projects if item.name == project_name),
            None,
        )
        if project is None:
            return Exception(f"Project '{project_name}' not found")
        repo = next((item for item in project.repos if item.name == repo_name), None)
        if repo is None:
            return Exception(f"Repo '{repo_name}' not found in project '{project_name}'")
        definition_root = resolve_definition_root(config_path)
        app_config = AppConfig.load()
        workspace_path = app_config.workspace.path if not isinstance(app_config, Exception) else "./.metagit"
        workspace_root = resolve_workspace_root(config_path, workspace_path)
        local_path: Optional[str] = None
        if repo.path:
            local_path = _resolve_manifest_path(str(repo.path), definition_root)
        else:
            candidate_path = Path(workspace_root) / project.name / repo.name
            if candidate_path.is_dir():
                local_path = str(candidate_path)
        return project, repo, local_path

    def _persist_repo(
        self,
        config: MetagitConfig,
        config_path: str,
        project_name: str,
        updated_repo: ProjectPath,
    ) -> Optional[Exception]:
        if not config.workspace:
            return Exception("No workspace configuration found")
        for project_index, project in enumerate(config.workspace.projects):
            if project.name != project_name:
                continue
            repos = list(project.repos)
            for repo_index, repo in enumerate(repos):
                if repo.name != updated_repo.name:
                    continue
                repos[repo_index] = updated_repo
                config.workspace.projects[project_index] = project.model_copy(update={"repos": repos})
                result = MetagitConfigManager(config_path=config_path).save_config(config, config_path)
                if isinstance(result, Exception):
                    return result
                return None
        return Exception(f"Repo '{updated_repo.name}' not found in project '{project_name}'")


__all__ = ["CiTargetService"]
