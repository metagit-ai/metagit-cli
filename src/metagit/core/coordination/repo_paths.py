#!/usr/bin/env python
"""Helpers for resolving managed repository paths for ACL operations."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.layout_resolver import find_project, find_repo, repo_mount_path


def parse_repository_ref(repository: str) -> tuple[str, str] | Exception:
    """Parse ``project/repo`` into components."""
    trimmed = repository.strip()
    if "/" not in trimmed:
        return ValueError(
            f"invalid repository {repository!r}; expected project/repo",
        )
    project, repo = trimmed.split("/", 1)
    if not project.strip() or not repo.strip() or "/" in repo:
        return ValueError(
            f"invalid repository {repository!r}; expected project/repo",
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
    "build_agent_branch_name",
    "parse_repository_ref",
    "resolve_repo_filesystem_path",
    "slugify_branch_suffix",
]
