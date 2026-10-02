#!/usr/bin/env python
"""Helpers for resolving managed repository paths for ACL operations."""

from __future__ import annotations

from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.layout_resolver import find_project, find_repo, repo_mount_path

SELF_REPOSITORY = "."
_SELF_REFS = {".", "self"}


def canonical_repository_ref(repository: str) -> str:
    """Map ``.`` and ``self`` to the reserved self-repo ref. Other refs pass through."""
    trimmed = repository.strip()
    if trimmed in _SELF_REFS:
        return SELF_REPOSITORY
    return trimmed


def is_self_repository(repository: str) -> bool:
    """Return True for the reserved refs that mean the definition-root git repo."""
    return repository.strip() in _SELF_REFS


def parse_repository_ref(repository: str) -> tuple[str, str] | Exception:
    """Parse ``project/repo`` into components. ``.`` and ``self`` parse as the self repo."""
    trimmed = canonical_repository_ref(repository)
    if trimmed == SELF_REPOSITORY:
        return "self", "self"
    if "/" not in trimmed:
        return ValueError(
            f"invalid repository {repository!r}; expected project/repo, or . / self for the definition repo",
        )
    project, repo = trimmed.split("/", 1)
    if not project.strip() or not repo.strip() or "/" in repo:
        return ValueError(
            f"invalid repository {repository!r}; expected project/repo, or . / self for the definition repo",
        )
    return project.strip(), repo.strip()


def resolve_repo_filesystem_path(
    *,
    session_root: str,
    sync_root: str,
    repository: str,
    definition_path: str | None = None,
) -> Path | Exception:
    """
    Resolve a managed repo checkout under the sync root.

    Falls back to ``sync_root/project/repo`` when the manifest entry is missing
    but the directory exists (useful in tests).
    """
    parsed = parse_repository_ref(repository)
    if isinstance(parsed, Exception):
        return parsed
    if is_self_repository(repository):
        return _resolve_self_repo(session_root=session_root, definition_path=definition_path)
    project_name, repo_name = parsed
    sync = Path(sync_root).expanduser().resolve()
    mount = repo_mount_path(sync, project_name, repo_name)

    config_path = definition_path or str(Path(session_root) / ".metagit.yml")
    manager = MetagitConfigManager(config_path=config_path)
    config = manager.load_config()
    if isinstance(config, MetagitConfig):
        project = find_project(config, project_name)
        if project is not None:
            repo = find_repo(project, repo_name)
            if repo is not None and repo.path:
                candidate = Path(repo.path).expanduser()
                if not candidate.is_absolute():
                    candidate = (Path(session_root) / candidate).resolve()
                else:
                    candidate = candidate.resolve()
                if candidate.is_dir():
                    return candidate
    if mount.is_dir():
        return mount
    # Allow direct path under sync root even if not yet in manifest.
    if mount.parent.is_dir() or sync.is_dir():
        return mount
    return FileNotFoundError(f"repository path not found: {repository}")


def _resolve_self_repo(*, session_root: str, definition_path: str | None) -> Path | Exception:
    """Git top level of the directory that holds the metagit definition."""
    start = Path(session_root).expanduser()
    if definition_path:
        candidate = Path(definition_path).expanduser()
        if not candidate.is_absolute():
            candidate = start / candidate
        candidate = candidate.resolve()
        start = candidate.parent if candidate.is_file() else candidate
    else:
        start = start.resolve()
    try:
        repo = Repo(str(start), search_parent_directories=True)
    except (InvalidGitRepositoryError, OSError) as exc:
        return FileNotFoundError(f"self repository is not inside a git checkout: {exc}")
    toplevel = repo.working_tree_dir
    if not toplevel:
        return FileNotFoundError("self repository has no working tree")
    return Path(toplevel).resolve()


def slugify_branch_suffix(text: str) -> str:
    """Normalize a short description for agent branch names."""
    cleaned = []
    for char in text.strip().lower():
        if char.isalnum():
            cleaned.append(char)
        elif char in {"-", "_", " "} and cleaned and cleaned[-1] != "-":
            cleaned.append("-")
    result = "".join(cleaned).strip("-")
    return result[:48]


def build_agent_branch_name(task_id: str, description: str | None = None) -> str:
    """Build ``agent/<task-id>`` or ``agent/<task-id>-<slug>``."""
    base = f"agent/{task_id.strip()}"
    if not description:
        return base
    slug = slugify_branch_suffix(description)
    return f"{base}-{slug}" if slug else base


__all__ = [
    "SELF_REPOSITORY",
    "build_agent_branch_name",
    "canonical_repository_ref",
    "is_self_repository",
    "parse_repository_ref",
    "resolve_repo_filesystem_path",
    "slugify_branch_suffix",
]
