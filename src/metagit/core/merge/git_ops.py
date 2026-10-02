#!/usr/bin/env python
"""Git helpers for RFC-0011 merge attempts.

Merges run in a temporary worktree created for that operation. The checkout
passed as ``repo_path`` is never checked out, and its index and working tree
are left alone. The target branch is updated only when it is not checked out
in any worktree.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import tempfile
from contextlib import contextmanager, suppress
from pathlib import Path, PurePosixPath
from typing import Iterator, Optional

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


def checked_out_paths(repo_path: str, branch: str) -> list[str] | Exception:
    """Return worktree paths where ``branch`` is the current branch."""
    try:
        repo = Repo(repo_path)
        output = repo.git.worktree("list", "--porcelain")
    except Exception as exc:  # noqa: BLE001
        return exc
    wanted = f"refs/heads/{branch}"
    paths: list[str] = []
    current: str | None = None
    for line in output.splitlines():
        if line.startswith("worktree "):
            current = line[len("worktree ") :]
            continue
        if line == f"branch {wanted}" and current:
            paths.append(current)
    return paths


def attempt_merge(
    repo_path: str,
    source_branch: str,
    target_branch: str,
    *,
    regenerate: dict[str, str] | None = None,
) -> MergeGitResult | Exception:
    """Merge ``source_branch`` into ``target_branch`` without touching ``repo_path``.

    Refuses when ``target_branch`` is checked out anywhere. There is no flag
    that overrides that refusal. ``regenerate`` maps a path glob to a command.
    When every conflicted path matches, the target side is kept and those
    commands rebuild the files inside the temporary worktree.
    """
    busy = checked_out_paths(repo_path, target_branch)
    if isinstance(busy, Exception):
        return busy
    if busy:
        listed = ", ".join(busy)
        return ValueError(
            f"refusing to merge into {target_branch!r}: it is checked out at {listed}. "
            "No flag overrides this; switch that checkout off the branch first.",
        )
    try:
        repo = Repo(repo_path)
    except Exception as exc:  # noqa: BLE001
        return exc
    if not any(head.name == target_branch for head in repo.heads):
        return ValueError(f"target branch not found: {target_branch}")
    if not any(head.name == source_branch for head in repo.heads):
        return ValueError(f"source branch not found: {source_branch}")

    parent = Path(tempfile.mkdtemp(prefix="metagit-merge-"))
    checkout = parent / "wt"
    try:
        repo.git.worktree("add", str(checkout), target_branch)
        work = Repo(str(checkout))
        try:
            work.git.merge(source_branch)
        except GitCommandError as exc:
            recovered = _maybe_regenerate(work, regenerate)
            if isinstance(recovered, Exception):
                return recovered
            if recovered is not None:
                return recovered
            return _conflict_result(work, exc)
        return MergeGitResult(ok=True, commit_sha=work.head.commit.hexsha)
    except Exception as exc:  # noqa: BLE001
        return exc
    finally:
        _remove_worktree(repo_path, checkout)
        shutil.rmtree(parent, ignore_errors=True)


@contextmanager
def detached_worktree(repo_path: str, commit_sha: str) -> Iterator[str]:
    """Yield a temporary detached checkout of ``commit_sha``, then remove it."""
    parent = Path(tempfile.mkdtemp(prefix="metagit-merge-validate-"))
    checkout = parent / "wt"
    repo = Repo(repo_path)
    repo.git.worktree("add", "--detach", str(checkout), commit_sha)
    try:
        yield str(checkout)
    finally:
        _remove_worktree(repo_path, checkout)
        shutil.rmtree(parent, ignore_errors=True)


def _maybe_regenerate(repo: Repo, regenerate: dict[str, str] | None) -> MergeGitResult | Exception | None:
    """Rebuild mapped conflicts. None means at least one path is outside the map."""
    if not regenerate:
        return None
    files = sorted(repo.index.unmerged_blobs().keys())
    if not files:
        return None
    commands = _regenerate_commands(files, regenerate)
    if commands is None:
        return None
    try:
        for path in files:
            repo.git.checkout("--ours", "--", path)
            repo.git.add("--", path)
        for command in commands:
            args = shlex.split(command)
            if not args:
                raise ValueError(f"merge.regenerate command is empty for {command!r}")
            completed = subprocess.run(
                args,
                cwd=str(repo.working_tree_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "").strip()
                raise Exception(f"merge.regenerate failed ({completed.returncode}): {command}: {detail}")
        for path in files:
            repo.git.add("--", path)
        repo.git.commit("--no-edit")
    except Exception as exc:  # noqa: BLE001
        with suppress(Exception):
            repo.git.merge("--abort")
        return exc
    return MergeGitResult(ok=True, commit_sha=repo.head.commit.hexsha)


def _regenerate_commands(files: list[str], regenerate: dict[str, str]) -> list[str] | None:
    commands: list[str] = []
    seen: set[str] = set()
    for path in files:
        matched = False
        for pattern, command in regenerate.items():
            if PurePosixPath(path).match(pattern):
                matched = True
                if command not in seen:
                    seen.add(command)
                    commands.append(command)
        if not matched:
            return None
    return commands


def _conflict_result(repo: Repo, exc: GitCommandError) -> MergeGitResult | Exception:
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


def _remove_worktree(repo_path: str, checkout: Path) -> None:
    if not checkout.exists():
        return
    try:
        Repo(repo_path).git.worktree("remove", "--force", str(checkout))
    except Exception:
        shutil.rmtree(checkout, ignore_errors=True)


__all__ = [
    "MergeGitResult",
    "attempt_merge",
    "checked_out_paths",
    "detached_worktree",
    "ensure_branch",
]
