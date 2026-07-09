#!/usr/bin/env python
"""GitPython helpers for RFC-0011 merge attempts."""

from __future__ import annotations

from typing import Optional

from git import GitCommandError, Repo
from pydantic import BaseModel

from metagit.core.merge.models import MergeConflict


class MergeGitResult(BaseModel):
    """Structured result from a local git merge attempt."""

    ok: bool
    commit_sha: Optional[str] = None
    conflict: Optional[MergeConflict] = None


def ensure_branch(repo_path: str, branch: str, start_point: str) -> None | Exception:
    """Create ``branch`` from ``start_point`` when it does not already exist."""
    try:
        repo = Repo(repo_path)
        if any(head.name == branch for head in repo.heads):
            return None
        repo.create_head(branch, start_point)
        return None
    except Exception as exc:  # noqa: BLE001
        return exc


def attempt_merge(repo_path: str, source_branch: str, target_branch: str) -> MergeGitResult | Exception:
    """Checkout ``target_branch`` and merge ``source_branch`` without pushing."""
    try:
        repo = Repo(repo_path)
        repo.git.checkout(target_branch)
        repo.git.merge(source_branch)
        return MergeGitResult(ok=True, commit_sha=repo.head.commit.hexsha)
    except GitCommandError as exc:
        conflict = _conflict_result(repo_path, exc)
        if isinstance(conflict, Exception):
            return conflict
        return conflict
    except Exception as exc:  # noqa: BLE001
        return exc


def _conflict_result(repo_path: str, exc: GitCommandError) -> MergeGitResult | Exception:
    repo = Repo(repo_path)
    files = sorted(repo.index.unmerged_blobs().keys())
    if not files:
        return exc
    try:
        repo.git.merge("--abort")
    except Exception as abort_exc:  # noqa: BLE001
        return abort_exc
    return MergeGitResult(
        ok=False,
        conflict=MergeConflict(
            files=files,
            message=f"Merge conflict while merging source branch: {exc.stderr or exc.stdout}",
        ),
    )


__all__ = [
    "MergeGitResult",
    "attempt_merge",
    "ensure_branch",
]
