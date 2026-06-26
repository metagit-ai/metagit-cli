#!/usr/bin/env python
"""
Workspace-scoped repository deduplication helpers (canonical store + symlinks).
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.utils.common import normalize_git_url


@dataclass(frozen=True)
class RepoIdentity:
    """Stable identity for a workspace repo entry."""

    repo_key: str
    url: Optional[str] = None
    local_path: Optional[str] = None


def build_repo_identity(repo: ProjectPath) -> Optional[RepoIdentity]:
    """
    Build a stable repo key for deduplication within one workspace manifest.

    Branch-specific entries (ref or branches) receive distinct keys.
    """
    branch_suffix = _branch_suffix(repo)
    if repo.url:
        normalized = normalize_git_url(str(repo.url)) or ""
        if not normalized:
            return None
        base_key = _slugify(normalized, digest_prefix="url")
        return RepoIdentity(
            repo_key=f"{base_key}{branch_suffix}",
            url=normalized,
        )
    if repo.path:
        resolved = str(Path(repo.path).expanduser().resolve())
        base_key = _slugify(resolved, digest_prefix="path")
        return RepoIdentity(
            repo_key=f"{base_key}{branch_suffix}",
            local_path=resolved,
        )
    return None


def find_duplicate_identities(
    config: MetagitConfig,
    repo: ProjectPath,
    *,
    exclude_project: Optional[str] = None,
    exclude_repo_name: Optional[str] = None,
) -> list[tuple[str, str]]:
    """Return (project_name, repo_name) pairs sharing the same identity as repo."""
    target = build_repo_identity(repo)
    if target is None or not config.workspace:
        return []
    matches: list[tuple[str, str]] = []
    for project in config.workspace.projects:
        for existing in project.repos:
            if exclude_project == project.name and exclude_repo_name == existing.name:
                continue
            existing_identity = build_repo_identity(existing)
            if existing_identity is not None and existing_identity.repo_key == target.repo_key:
                matches.append((project.name, existing.name))
    return matches


def canonical_path(
    workspace_path: Path,
    dedupe: WorkspaceDedupeConfig,
    repo_key: str,
) -> Path:
    """Absolute path to the canonical checkout directory for repo_key."""
    return (workspace_path / dedupe.canonical_dir / repo_key).resolve()


def project_mount_path(
    workspace_path: Path,
    project_name: str,
    repo_name: str,
) -> Path:
    """Absolute path where a project exposes a repo (symlink or directory)."""
    return (workspace_path / project_name / repo_name).resolve()


def ensure_symlink(mount: Path, target: Path) -> tuple[bool, Optional[str]]:
    """
    Ensure mount is a symlink to target.

    Returns (changed, error_message).
    """
    target_resolved = target.resolve()
    if mount.is_symlink():
        try:
            current = Path(os.readlink(mount))
            current = (mount.parent / current).resolve() if not current.is_absolute() else current.resolve()
            if current == target_resolved:
                return False, None
        except OSError:
            pass
        mount.unlink(missing_ok=True)
    elif mount.exists():
        return False, f"mount exists and is not a symlink: {mount}"

    mount.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target_resolved, mount, target_is_directory=target_resolved.is_dir())
        return True, None
    except OSError as exc:
        return False, str(exc)


def list_canonical_references(
    config: MetagitConfig,
    workspace_path: Path,
    dedupe: WorkspaceDedupeConfig,
) -> dict[str, list[tuple[str, str]]]:
    """
    Map repo_key -> list of (project_name, repo_name) manifest entries referencing it.
    """
    _ = workspace_path
    _ = dedupe
    references: dict[str, list[tuple[str, str]]] = {}
    if not config.workspace:
        return references
    for project in config.workspace.projects:
        for repo in project.repos:
            identity = build_repo_identity(repo)
            if identity is None:
                continue
            references.setdefault(identity.repo_key, []).append((project.name, repo.name))
    return references


def list_orphan_canonical_dirs(
    workspace_path: Path,
    dedupe: WorkspaceDedupeConfig,
    references: dict[str, list[tuple[str, str]]],
) -> list[Path]:
    """Canonical directories with no manifest reference (by repo_key)."""
    root = workspace_path / dedupe.canonical_dir
    if not root.is_dir():
        return []
    referenced = set(references.keys())
    orphans: list[Path] = []
    for entry in root.iterdir():
        if entry.is_dir() and entry.name not in referenced:
            orphans.append(entry.resolve())
    return sorted(orphans, key=lambda item: item.name)


def _branch_suffix(repo: ProjectPath) -> str:
    if repo.ref:
        return f"--ref-{_slugify(str(repo.ref), digest_prefix='ref')}"
    if repo.branches:
        joined = "-".join(sorted(str(branch) for branch in repo.branches))
        return f"--branches-{_slugify(joined, digest_prefix='br')}"
    return ""


def _slugify(value: str, *, digest_prefix: str) -> str:
    compact = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    if len(compact) <= 80 and compact:
        return compact
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    short = compact[:40].strip("-") if compact else digest_prefix
    return f"{short}-{digest}"
