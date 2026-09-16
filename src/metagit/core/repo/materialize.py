#!/usr/bin/env python
"""Turn an indexed external repository into a local workspace checkout."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from git import GitCommandError, Repo
from pydantic import BaseModel

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.repo.identity import identity_from_git_url
from metagit.core.repo.models import RepositoryNode
from metagit.core.repo.resolver import RepositoryResolver
from metagit.core.workspace.catalog_service import WorkspaceCatalogService


class RepoMaterializeError(BaseModel):
    """Structured materialize failure."""

    kind: str
    message: str


class RepoMaterializeResult(BaseModel):
    """Outcome of materializing an external repository."""

    ok: bool
    dry_run: bool = False
    identity: str = ""
    name: str = ""
    project_name: str = ""
    url: Optional[str] = None
    mount_path: Optional[str] = None
    cloned: bool = False
    already_materialized: bool = False
    manifest_updated: bool = False
    error: Optional[RepoMaterializeError] = None


class RepoMaterializeService:
    """Clone an indexed repository and enroll it in the workspace catalog."""

    def __init__(
        self,
        *,
        catalog: WorkspaceCatalogService | None = None,
        resolver: RepositoryResolver | None = None,
    ) -> None:
        self._catalog = catalog or WorkspaceCatalogService()
        self._resolver = resolver

    def materialize(
        self,
        config: MetagitConfig,
        config_path: str,
        identifier: str,
        *,
        workspace_root: str,
        project_name: str | None = None,
        dry_run: bool = False,
        clone: bool = True,
        index_home: Path | None = None,
    ) -> RepoMaterializeResult:
        resolver = self._resolver or RepositoryResolver(config, index_home=index_home)
        resolved = resolver.resolve(identifier)
        if isinstance(resolved, Exception):
            return _fail("resolve_failed", str(resolved))
        if resolved is None:
            return _fail("not_found", f"repository '{identifier}' is not a known node")

        result = RepoMaterializeResult(
            ok=False,
            dry_run=dry_run,
            identity=resolved.identity,
            name=resolved.name,
        )
        if resolved.presence == "materialized" and resolved.project_name:
            result.ok = True
            result.already_materialized = True
            result.project_name = resolved.project_name
            result.url = resolved.url or resolved.clone_url
            result.mount_path = resolved.local_path
            return result

        target_project = project_name or _default_project(config)
        if not target_project:
            result.error = RepoMaterializeError(
                kind="project_required",
                message="workspace has multiple projects; pass --project",
            )
            return result
        result.project_name = target_project

        clone_url = resolved.clone_url or resolved.url
        if not clone_url:
            result.error = RepoMaterializeError(
                kind="no_url",
                message=f"repository '{resolved.name}' has no clone URL",
            )
            return result
        result.url = clone_url
        mount = Path(workspace_root).expanduser() / target_project / resolved.name
        result.mount_path = str(mount)

        if dry_run:
            result.ok = True
            return result

        entry = ProjectPath(
            name=resolved.name,
            description=resolved.description,
            url=clone_url,
            language=resolved.language,
            source_provider=resolved.provider,
            source_namespace=resolved.organization,
            tags={"canonical_identity": resolved.identity} if resolved.identity else {},
        )
        mutation = self._catalog.add_repo(
            config,
            config_path,
            project_name=target_project,
            repo=entry,
            ensure=True,
        )
        if not mutation.ok:
            message = mutation.error.message if mutation.error else "catalog add failed"
            kind = mutation.error.kind if mutation.error else "catalog_error"
            result.error = RepoMaterializeError(kind=kind, message=message)
            return result
        result.manifest_updated = mutation.operation != "noop"

        if clone and not mount.exists():
            try:
                mount.parent.mkdir(parents=True, exist_ok=True)
                Repo.clone_from(clone_url, str(mount))
                result.cloned = True
            except GitCommandError as exc:
                result.error = RepoMaterializeError(kind="clone_failed", message=str(exc))
                return result

        result.ok = True
        return result


def identity_stable_after_materialize(before: RepositoryNode, after: RepositoryNode) -> bool:
    """True when materialization kept the canonical identity."""
    if before.identity.startswith("github://") or after.identity.startswith("github://"):
        return before.identity == after.identity
    local_url = after.url or after.clone_url
    derived = identity_from_git_url(local_url)
    return derived == before.identity if derived else before.name == after.name


def _default_project(config: MetagitConfig) -> str | None:
    if config.workspace is None or not config.workspace.projects:
        return None
    if len(config.workspace.projects) == 1:
        return config.workspace.projects[0].name
    return None


def _fail(kind: str, message: str) -> RepoMaterializeResult:
    return RepoMaterializeResult(
        ok=False,
        error=RepoMaterializeError(kind=kind, message=message),
    )
