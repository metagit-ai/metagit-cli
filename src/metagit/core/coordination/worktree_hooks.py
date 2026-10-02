#!/usr/bin/env python
"""Post-create hooks for agent worktrees.

Symlink and copy targets must be gitignored in the source repository so a hook
cannot place a tracked secret into the new checkout.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from git import GitCommandError, Repo

from metagit.core.appconfig.models import WorktreePostCreateHook

_CONFIG_KEY = "coordination.worktree.post_create"


def apply_post_create(
    *,
    source_repo: Path,
    checkout: Path,
    hooks: list[WorktreePostCreateHook],
) -> None | Exception:
    """Run hooks in order. Return an exception without leaving a partial success hidden."""
    if not hooks:
        return None
    try:
        repo = Repo(str(source_repo))
    except (GitCommandError, OSError, ValueError) as exc:
        return Exception(f"cannot inspect {source_repo} for {_CONFIG_KEY}: {exc}")
    for hook in hooks:
        if hook.symlink:
            result = _symlink(repo, source_repo, checkout, hook.symlink)
        elif hook.copy_path:
            result = _copy(repo, source_repo, checkout, hook.copy_path)
        elif hook.run:
            result = _run(checkout, hook.run)
        else:
            result = ValueError(f"{_CONFIG_KEY} entry needs exactly one of symlink, copy, or run")
        if isinstance(result, Exception):
            return result
    return None


def _relative_path(value: str) -> str | Exception:
    raw = value.strip()
    if not raw or raw.startswith(("/", "\\")) or ".." in Path(raw).parts:
        return ValueError(
            f"refusing {_CONFIG_KEY} path {value!r}: it must be a relative path inside the repository. "
            f"Set {_CONFIG_KEY} to a repo-relative gitignored path.",
        )
    return raw.replace("\\", "/")


def _require_ignored(repo: Repo, relative: str) -> None | Exception:
    try:
        repo.git.check_ignore("--", relative)
    except GitCommandError:
        return ValueError(
            f"refusing {_CONFIG_KEY} path {relative!r}: it is not gitignored. "
            f"Set {_CONFIG_KEY} to a gitignored path so the hook cannot stage a tracked file.",
        )
    return None


def _symlink(repo: Repo, source_repo: Path, checkout: Path, relative: str) -> None | Exception:
    cleaned = _relative_path(relative)
    if isinstance(cleaned, Exception):
        return cleaned
    ignored = _require_ignored(repo, cleaned)
    if isinstance(ignored, Exception):
        return ignored
    source = source_repo / cleaned
    if not source.exists():
        return FileNotFoundError(f"{_CONFIG_KEY} symlink source does not exist: {cleaned}")
    dest = checkout / cleaned
    if dest.exists() or dest.is_symlink():
        return ValueError(f"{_CONFIG_KEY} symlink destination already exists: {cleaned}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(source.resolve())
    return None


def _copy(repo: Repo, source_repo: Path, checkout: Path, relative: str) -> None | Exception:
    cleaned = _relative_path(relative)
    if isinstance(cleaned, Exception):
        return cleaned
    ignored = _require_ignored(repo, cleaned)
    if isinstance(ignored, Exception):
        return ignored
    source = source_repo / cleaned
    if not source.exists():
        return FileNotFoundError(f"{_CONFIG_KEY} copy source does not exist: {cleaned}")
    dest = checkout / cleaned
    if dest.exists() or dest.is_symlink():
        return ValueError(f"{_CONFIG_KEY} copy destination already exists: {cleaned}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, dest)
    else:
        shutil.copy2(source, dest)
    return None


def _run(checkout: Path, command: str) -> None | Exception:
    try:
        args = shlex.split(command)
    except ValueError as exc:
        return ValueError(f"{_CONFIG_KEY} run command is not parseable: {exc}")
    if not args:
        return ValueError(f"{_CONFIG_KEY} run command is empty")
    completed = subprocess.run(
        args,
        cwd=str(checkout),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return Exception(f"{_CONFIG_KEY} run failed ({completed.returncode}): {command}: {detail}")
    return None


__all__ = ["apply_post_create"]
