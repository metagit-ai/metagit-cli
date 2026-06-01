#!/usr/bin/env python
"""
Rename and move workspace projects and repositories (manifest + sync layout).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Optional

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.workspace import workspace_dedupe
from metagit.core.workspace.catalog_models import CatalogError
from metagit.core.workspace.layout_executor import LayoutExecutionError, apply_plan
from metagit.core.workspace.layout_models import (
    LayoutMutationResult,
    LayoutPlan,
    LayoutStep,
)
from metagit.core.workspace.layout_resolver import (
    dedupe_enabled,
    find_project,
    find_repo,
    project_dir,
    repo_mount_path,
    sync_root_path,
    validate_layout_name,
)
from metagit.core.workspace.protection import project_is_protected, repo_is_protected


class WorkspaceLayoutService:
    """Rename/move workspace catalog entries and aligned sync folders."""

    def rename_project(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_path: str,
        *,
        from_name: str,
        to_name: str,
        dedupe: Optional[WorkspaceDedupeConfig] = None,
        dry_run: bool = False,
        move_disk: bool = True,
        update_sessions: bool = True,
        force: bool = False,
    ) -> LayoutMutationResult:
        """Rename a workspace project in the manifest and on disk."""
        _ = dedupe
        source = from_name.strip()
        target = to_name.strip()
        err = validate_layout_name(source, label="from_name") or validate_layout_name(
            target, label="to_name"
        )
        if err:
            return self._error(
                "rename", "project", source, kind="invalid_name", message=err
            )
        if source == target:
            return self._error(
                "rename",
                "project",
                source,
                kind="noop",
                message="source and target names are the same",
            )
        project = find_project(config, source)
        if project is None:
            return self._error(
                "rename",
                "project",
                source,
                kind="not_found",
                message=f"project '{source}' not found",
            )
        if project_is_protected(project) and not force:
            return self._error(
                "rename",
                "project",
                source,
                kind="protected",
                message=f"project '{source}' is protected (use force=True)",
            )
        if find_project(config, target) is not None:
            return self._error(
                "rename",
                "project",
                source,
                kind="already_exists",
                message=f"project '{target}' already exists",
            )

        root = sync_root_path(workspace_path)
        plan = LayoutPlan(
            operation="rename_project",
            dry_run=dry_run,
            manifest_changes=[f"project.name: {source} -> {target}"],
        )
        old_dir = project_dir(root, source)
        new_dir = project_dir(root, target)
        if move_disk and old_dir.exists():
            if new_dir.exists() and not force:
                return self._error(
                    "rename",
                    "project",
                    source,
                    kind="target_exists",
                    message=f"sync folder already exists: {new_dir}",
                )
            plan.disk_steps.append(
                LayoutStep(
                    action="rename",
                    source=str(old_dir),
                    target=str(new_dir),
                )
            )
        if move_disk and new_dir.exists():
            plan.disk_steps.append(
                LayoutStep(
                    action="regenerate_vscode",
                    source=str(new_dir),
                    target=target,
                )
            )

        if dry_run:
            return self._success(
                "rename",
                "project",
                target,
                config_path=config_path,
                plan=plan,
            )

        working = copy.deepcopy(config)
        working_project = find_project(working, source)
        if working_project is None:
            return self._error(
                "rename",
                "project",
                source,
                kind="not_found",
                message=f"project '{source}' not found",
            )
        working_project.name = target

        try:
            if move_disk:
                apply_plan(plan, dry_run=False)
            save_err = self._save(working, config_path)
            if save_err:
                return self._error(
                    "rename",
                    "project",
                    source,
                    kind="save_failed",
                    message=str(save_err),
                )
            project.name = target
            if update_sessions:
                store = SessionStore(workspace_root=str(root))
                if store.rename_project_session(from_name=source, to_name=target):
                    plan.disk_steps.append(
                        LayoutStep(
                            action="migrate_session",
                            source=f"{source}.json",
                            target=f"{target}.json",
                            applied=True,
                        )
                    )
                meta = store.get_workspace_meta()
                if meta.active_project == source:
                    store.set_active_project(project_name=target)
        except LayoutExecutionError as exc:
            return self._error(
                "rename",
                "project",
                source,
                kind="disk_failed",
                message=str(exc),
            )

        return self._success(
            "rename",
            "project",
            target,
            config_path=config_path,
            plan=plan,
            manifest_updated=True,
        )

    def rename_repo(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_path: str,
        *,
        project_name: str,
        from_name: str,
        to_name: str,
        dedupe: Optional[WorkspaceDedupeConfig] = None,
        dry_run: bool = False,
        move_disk: bool = True,
        force: bool = False,
    ) -> LayoutMutationResult:
        """Rename a repository entry and its sync mount when present."""
        project_key = project_name.strip()
        source = from_name.strip()
        target = to_name.strip()
        err = validate_layout_name(source, label="from_name") or validate_layout_name(
            target, label="to_name"
        )
        if err:
            return self._error(
                "rename",
                "repo",
                project_key,
                repo_name=source,
                kind="invalid_name",
                message=err,
            )
        if project_key == "local":
            return self._error(
                "rename",
                "repo",
                project_key,
                repo_name=source,
                kind="unsupported",
                message="the local project does not support layout disk operations",
            )
        if source == target:
            return self._error(
                "rename",
                "repo",
                project_key,
                repo_name=source,
                kind="noop",
                message="source and target names are the same",
            )
        project = find_project(config, project_key)
        if project is None:
            return self._error(
                "rename",
                "repo",
                project_key,
                repo_name=source,
                kind="project_not_found",
                message=f"project '{project_key}' not found",
            )
        repo = find_repo(project, source)
        if repo is None:
            return self._error(
                "rename",
                "repo",
                project_key,
                repo_name=source,
                kind="not_found",
                message=f"repo '{source}' not found in project '{project_key}'",
            )
        if repo_is_protected(project, repo) and not force:
            return self._error(
                "rename",
                "repo",
                project_key,
                repo_name=source,
                kind="protected",
                message=f"repo '{source}' is protected (use force=True)",
            )
        if find_repo(project, target) is not None:
            return self._error(
                "rename",
                "repo",
                project_key,
                repo_name=source,
                kind="already_exists",
                message=f"repo '{target}' already exists in project '{project_key}'",
            )

        root = sync_root_path(workspace_path)
        plan = LayoutPlan(
            operation="rename_repo",
            dry_run=dry_run,
            manifest_changes=[
                f"{project_key}.repos[].name: {source} -> {target}",
            ],
        )
        plan.warnings.extend(
            self._git_warnings(repo_mount_path(root, project_key, source))
        )

        old_mount = repo_mount_path(root, project_key, source)
        new_mount = repo_mount_path(root, project_key, target)
        if move_disk and old_mount.exists():
            if new_mount.exists() and not force:
                return self._error(
                    "rename",
                    "repo",
                    project_key,
                    repo_name=source,
                    kind="target_exists",
                    message=f"mount already exists: {new_mount}",
                )
            if dedupe_enabled(dedupe) and old_mount.is_symlink():
                identity = workspace_dedupe.build_repo_identity(repo)
                if identity and dedupe:
                    canonical = workspace_dedupe.canonical_path(
                        root, dedupe, identity.repo_key
                    )
                    plan.disk_steps.append(
                        LayoutStep(action="unlink", source=str(old_mount))
                    )
                    plan.disk_steps.append(
                        LayoutStep(
                            action="symlink",
                            source=str(canonical),
                            target=str(new_mount),
                        )
                    )
                else:
                    plan.disk_steps.append(
                        LayoutStep(
                            action="rename",
                            source=str(old_mount),
                            target=str(new_mount),
                        )
                    )
            else:
                plan.disk_steps.append(
                    LayoutStep(
                        action="rename",
                        source=str(old_mount),
                        target=str(new_mount),
                    )
                )

        proj_path = project_dir(root, project_key)
        if move_disk and proj_path.exists():
            plan.disk_steps.append(
                LayoutStep(
                    action="regenerate_vscode",
                    source=str(proj_path),
                    target=project_key,
                )
            )

        if dry_run:
            return self._success(
                "rename",
                "repo",
                project_key,
                repo_name=target,
                config_path=config_path,
                plan=plan,
            )

        repo.name = target
        try:
            if move_disk:
                apply_plan(plan, dry_run=False)
            save_err = self._save(config, config_path)
            if save_err:
                repo.name = source
                return self._error(
                    "rename",
                    "repo",
                    project_key,
                    repo_name=source,
                    kind="save_failed",
                    message=str(save_err),
                )
        except LayoutExecutionError as exc:
            repo.name = source
            return self._error(
                "rename",
                "repo",
                project_key,
                repo_name=source,
                kind="disk_failed",
                message=str(exc),
            )

        return self._success(
            "rename",
            "repo",
            project_key,
            repo_name=target,
            config_path=config_path,
            plan=plan,
            manifest_updated=True,
        )

    def move_repo(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_path: str,
        *,
        repo_name: str,
        from_project: str,
        to_project: str,
        dedupe: Optional[WorkspaceDedupeConfig] = None,
        dry_run: bool = False,
        move_disk: bool = True,
        force: bool = False,
    ) -> LayoutMutationResult:
        """Move a repository entry from one project to another."""
        source_project_name = from_project.strip()
        target_project_name = to_project.strip()
        repo_key = repo_name.strip()
        if source_project_name == "local" or target_project_name == "local":
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="unsupported",
                message="the local project does not support layout disk operations",
            )
        err = validate_layout_name(repo_key, label="repo_name")
        if err:
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="invalid_name",
                message=err,
            )
        if source_project_name == target_project_name:
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="noop",
                message="source and target projects are the same",
            )

        source_project = find_project(config, source_project_name)
        if source_project is None:
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="project_not_found",
                message=f"project '{source_project_name}' not found",
            )
        target_project = find_project(config, target_project_name)
        if target_project is None:
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="project_not_found",
                message=f"project '{target_project_name}' not found",
            )
        repo = find_repo(source_project, repo_key)
        if repo is None:
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="not_found",
                message=(
                    f"repo '{repo_key}' not found in project '{source_project_name}'"
                ),
            )
        if project_is_protected(source_project) and not force:
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="protected",
                message=(
                    f"project '{source_project_name}' is protected (use force=True)"
                ),
            )
        if project_is_protected(target_project) and not force:
            return self._error(
                "move",
                "repo",
                target_project_name,
                repo_name=repo_key,
                kind="protected",
                message=(
                    f"project '{target_project_name}' is protected (use force=True)"
                ),
            )
        if repo_is_protected(source_project, repo) and not force:
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="protected",
                message=f"repo '{repo_key}' is protected (use force=True)",
            )

        existing_target = find_repo(target_project, repo_key)
        if existing_target is not None and not force:
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="already_exists",
                message=(
                    f"repo '{repo_key}' already exists in project '{target_project_name}'"
                ),
            )

        root = sync_root_path(workspace_path)
        plan = LayoutPlan(
            operation="move_repo",
            dry_run=dry_run,
            manifest_changes=[
                f"move {repo_key}: {source_project_name} -> {target_project_name}",
            ],
        )
        old_mount = repo_mount_path(root, source_project_name, repo_key)
        new_mount = repo_mount_path(root, target_project_name, repo_key)
        plan.warnings.extend(self._git_warnings(old_mount))

        if move_disk and old_mount.exists():
            if new_mount.exists() and not force:
                return self._error(
                    "move",
                    "repo",
                    source_project_name,
                    repo_name=repo_key,
                    kind="target_exists",
                    message=f"mount already exists: {new_mount}",
                )
            if dedupe_enabled(dedupe) and old_mount.is_symlink() and dedupe:
                identity = workspace_dedupe.build_repo_identity(repo)
                if identity:
                    canonical = workspace_dedupe.canonical_path(
                        root, dedupe, identity.repo_key
                    )
                    plan.disk_steps.append(
                        LayoutStep(action="unlink", source=str(old_mount))
                    )
                    plan.disk_steps.append(
                        LayoutStep(
                            action="mkdir",
                            target=str(new_mount.parent),
                        )
                    )
                    plan.disk_steps.append(
                        LayoutStep(
                            action="symlink",
                            source=str(canonical),
                            target=str(new_mount),
                        )
                    )
            else:
                plan.disk_steps.append(
                    LayoutStep(
                        action="move",
                        source=str(old_mount),
                        target=str(new_mount),
                    )
                )

        for proj_name in (source_project_name, target_project_name):
            proj_path = project_dir(root, proj_name)
            if move_disk and proj_path.exists():
                plan.disk_steps.append(
                    LayoutStep(
                        action="regenerate_vscode",
                        source=str(proj_path),
                        target=proj_name,
                    )
                )

        if dry_run:
            return self._success(
                "move",
                "repo",
                target_project_name,
                repo_name=repo_key,
                from_project=source_project_name,
                to_project=target_project_name,
                config_path=config_path,
                plan=plan,
            )

        if existing_target is not None and force:
            target_project.repos = [
                item for item in target_project.repos if item.name != repo_key
            ]

        pop_index = next(
            index
            for index, item in enumerate(source_project.repos)
            if item.name == repo_key
        )
        moved_repo = source_project.repos.pop(pop_index)
        target_project.repos.append(moved_repo)

        try:
            if move_disk:
                apply_plan(plan, dry_run=False)
            save_err = self._save(config, config_path)
            if save_err:
                target_project.repos.pop()
                source_project.repos.append(moved_repo)
                return self._error(
                    "move",
                    "repo",
                    source_project_name,
                    repo_name=repo_key,
                    kind="save_failed",
                    message=str(save_err),
                )
        except LayoutExecutionError as exc:
            target_project.repos = [
                item for item in target_project.repos if item.name != repo_key
            ]
            source_project.repos.append(moved_repo)
            return self._error(
                "move",
                "repo",
                source_project_name,
                repo_name=repo_key,
                kind="disk_failed",
                message=str(exc),
            )

        return self._success(
            "move",
            "repo",
            target_project_name,
            repo_name=repo_key,
            from_project=source_project_name,
            to_project=target_project_name,
            config_path=config_path,
            plan=plan,
            manifest_updated=True,
        )

    def _git_warnings(self, mount: Path) -> list[str]:
        """Warn when a git checkout under mount has a dirty working tree."""
        warnings: list[str] = []
        git_dir = mount / ".git"
        if not git_dir.exists():
            return warnings
        try:
            import git

            repo = git.Repo(str(mount))
            if repo.is_dirty(untracked_files=True):
                warnings.append(f"git working tree has uncommitted changes: {mount}")
        except Exception as exc:
            warnings.append(f"could not inspect git status at {mount}: {exc}")
        return warnings

    def _save(self, config: MetagitConfig, config_path: str) -> Optional[Exception]:
        manager = MetagitConfigManager(metagit_config=config)
        result = manager.save_config(config, Path(config_path))
        if isinstance(result, Exception):
            return result
        return None

    def _error(
        self,
        operation: str,
        entity: str,
        project_name: str,
        *,
        kind: str,
        message: str,
        repo_name: Optional[str] = None,
    ) -> LayoutMutationResult:
        return LayoutMutationResult(
            ok=False,
            error=CatalogError(kind=kind, message=message),
            entity="repo" if entity == "repo" else "project",
            operation="move" if operation == "move" else "rename",
            project_name=project_name,
            repo_name=repo_name,
            config_path="",
        )

    def _success(
        self,
        operation: str,
        entity: str,
        project_name: str,
        *,
        config_path: str,
        plan: LayoutPlan,
        repo_name: Optional[str] = None,
        from_project: Optional[str] = None,
        to_project: Optional[str] = None,
        manifest_updated: bool = False,
    ) -> LayoutMutationResult:
        data: dict[str, Any] = {
            "dry_run": plan.dry_run,
            "manifest_changes": plan.manifest_changes,
            "disk_steps": [step.model_dump(mode="json") for step in plan.disk_steps],
            "warnings": plan.warnings,
            "manifest_updated": manifest_updated,
        }
        return LayoutMutationResult(
            ok=True,
            entity="repo" if entity == "repo" else "project",
            operation="move" if operation == "move" else "rename",
            project_name=project_name,
            repo_name=repo_name,
            from_project=from_project,
            to_project=to_project,
            config_path=config_path,
            data=data,
        )
