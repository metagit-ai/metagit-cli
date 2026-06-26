#!/usr/bin/env python
"""Promote a local-path workspace repo entry to a git-managed clone."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.models import GitUrl, ProjectPath
from metagit.core.utils.common import is_git_repository
from metagit.core.workspace.layout_resolver import find_project
from metagit.core.workspace.protection import repo_is_protected
from metagit.core.workspace.workspace_dedupe import find_duplicate_identities


class RepoPromoteError(BaseModel):
    """Structured error for repo promote operations."""

    kind: str
    message: str


class RepoPromoteResult(BaseModel):
    """Outcome of promoting a local-path repo to a git-managed clone."""

    ok: bool
    dry_run: bool = False
    project_name: str = ""
    repo_name: str = ""
    source_path: Optional[str] = None
    url: Optional[str] = None
    mount_path: Optional[str] = None
    manifest_updated: bool = False
    mount_removed: bool = False
    synced: bool = False
    error: Optional[RepoPromoteError] = None


def resolve_git_remote_url(
    source_path: Path,
    *,
    remote_name: str = "origin",
) -> Optional[str]:
    """Return the fetch URL for ``remote_name``, or None when unavailable."""
    try:
        repo = Repo(source_path)
        return repo.remote(remote_name).url or None
    except (InvalidGitRepositoryError, NoSuchPathError, ValueError, IndexError):
        return None


class RepoPromoteService:
    """Promote local-path manifest entries into git-managed workspace clones."""

    def promote(
        self,
        config: MetagitConfig,
        config_path: str,
        *,
        workspace_root: str,
        project_name: str,
        repo_name: str,
        project_manager: ProjectManager,
        url_override: Optional[str] = None,
        remote_name: str = "origin",
        dry_run: bool = False,
        force: bool = False,
    ) -> RepoPromoteResult:
        """Replace a ``path`` entry with a ``url`` entry and clone into the sync folder."""
        base = RepoPromoteResult(
            ok=False,
            dry_run=dry_run,
            project_name=project_name,
            repo_name=repo_name,
        )
        project = find_project(config, project_name)
        if project is None:
            base.error = RepoPromoteError(
                kind="project_not_found",
                message=f"project '{project_name}' not found",
            )
            return base

        repo_entry = _find_repo(project.repos, repo_name)
        if repo_entry is None:
            base.error = RepoPromoteError(
                kind="repo_not_found",
                message=f"repo '{repo_name}' not found in project '{project_name}'",
            )
            return base

        if repo_is_protected(project, repo_entry) and not force:
            base.error = RepoPromoteError(
                kind="protected",
                message=(f"repo '{repo_name}' is protected (use force=True to promote)"),
            )
            return base

        if not repo_entry.path:
            base.error = RepoPromoteError(
                kind="not_local_path",
                message=(f"repo '{repo_name}' has no local path; promote applies only to path-based entries"),
            )
            return base

        source_path = Path(repo_entry.path).expanduser().resolve()
        base.source_path = str(source_path)
        if not source_path.exists():
            base.error = RepoPromoteError(
                kind="source_missing",
                message=f"source path does not exist: {source_path}",
            )
            return base

        resolved_url = _resolve_promote_url(
            repo_entry=repo_entry,
            source_path=source_path,
            url_override=url_override,
            remote_name=remote_name,
        )
        if resolved_url is None:
            base.error = RepoPromoteError(
                kind="no_url",
                message=(
                    "could not resolve a git remote URL; pass url= or ensure the source is a git repo with origin"
                ),
            )
            return base

        try:
            GitUrl.validate(resolved_url, None)
        except ValueError as exc:
            base.error = RepoPromoteError(
                kind="invalid_url",
                message=str(exc),
            )
            return base

        workspace = Path(workspace_root).expanduser().resolve()
        mount = workspace / project_name / repo_name
        base.url = resolved_url
        base.mount_path = str(mount)

        promoted = repo_entry.model_copy(
            update={"path": None, "url": resolved_url},
        )
        duplicates = find_duplicate_identities(
            config,
            promoted,
            exclude_project=project_name,
            exclude_repo_name=repo_name,
        )
        if duplicates:
            locations = ", ".join(f"{proj}/{name}" for proj, name in duplicates)
            base.error = RepoPromoteError(
                kind="duplicate_identity",
                message=(
                    f"url already registered as {locations}; remove the duplicate entry or enable workspace dedupe"
                ),
            )
            return base

        if dry_run:
            return RepoPromoteResult(
                ok=True,
                dry_run=True,
                project_name=project_name,
                repo_name=repo_name,
                source_path=str(source_path),
                url=resolved_url,
                mount_path=str(mount),
                mount_removed=mount.exists() or mount.is_symlink(),
            )

        mount_removed = False
        if mount.exists() or mount.is_symlink():
            try:
                project_manager.remove_sync_directory(mount)
                mount_removed = True
            except OSError as exc:
                base.error = RepoPromoteError(
                    kind="mount_remove_failed",
                    message=str(exc),
                )
                return base

        repo_entry.path = None
        repo_entry.url = resolved_url

        save_err = _save_config(config, config_path)
        if save_err is not None:
            base.error = RepoPromoteError(
                kind="save_failed",
                message=str(save_err),
            )
            return base

        synced = project_manager.sync(project)
        if not synced:
            base.error = RepoPromoteError(
                kind="sync_failed",
                message="project sync failed after manifest update",
            )
            base.manifest_updated = True
            base.mount_removed = mount_removed
            return base

        return RepoPromoteResult(
            ok=True,
            dry_run=False,
            project_name=project_name,
            repo_name=repo_name,
            source_path=str(source_path),
            url=resolved_url,
            mount_path=str(mount),
            manifest_updated=True,
            mount_removed=mount_removed,
            synced=True,
        )


def _find_repo(repos: list[ProjectPath], repo_name: str) -> Optional[ProjectPath]:
    trimmed = repo_name.strip()
    for repo in repos:
        if repo.name == trimmed:
            return repo
    return None


def _resolve_promote_url(
    *,
    repo_entry: ProjectPath,
    source_path: Path,
    url_override: Optional[str],
    remote_name: str,
) -> Optional[str]:
    if url_override and url_override.strip():
        return url_override.strip()
    if repo_entry.url:
        return str(repo_entry.url)
    if is_git_repository(source_path):
        return resolve_git_remote_url(source_path, remote_name=remote_name)
    return None


def _save_config(config: MetagitConfig, config_path: str) -> Optional[Exception]:
    manager = MetagitConfigManager(metagit_config=config)
    result = manager.save_config(config, Path(config_path))
    if isinstance(result, Exception):
        return result
    return None
