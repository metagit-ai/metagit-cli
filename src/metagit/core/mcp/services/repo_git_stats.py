#!/usr/bin/env python
"""
Git statistics helpers for repository inspect and snapshot flows.
"""

from datetime import datetime, timezone
from typing import Optional

from git import Repo
from git.exc import GitCommandError


def inspect_repo_state(repo_path: str) -> dict[str, str | bool | int | float | None]:
    """Return branch, dirty flag, ahead/behind, uncommitted count, and age metrics."""
    try:
        repo = Repo(repo_path)
        branch = str(repo.active_branch.name) if not repo.head.is_detached else "DETACHED"
        dirty = repo.is_dirty(untracked_files=True)
        ahead, behind = _ahead_behind(repo=repo)
        uncommitted = _uncommitted_count(repo=repo, dirty=dirty)
        head_age_days = head_commit_age_days(repo=repo)
        merge_age_days = merge_base_age_days(repo=repo)
        return {
            "ok": True,
            "branch": branch,
            "dirty": dirty,
            "ahead": ahead,
            "behind": behind,
            "uncommitted_count": uncommitted,
            "head_commit_age_days": head_age_days,
            "merge_base_age_days": merge_age_days,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "branch": None,
            "dirty": None,
            "ahead": None,
            "behind": None,
            "uncommitted_count": None,
            "head_commit_age_days": None,
            "merge_base_age_days": None,
        }


def _ahead_behind(repo: Repo) -> tuple[Optional[int], Optional[int]]:
    """Return ahead and behind counts relative to upstream when configured."""
    try:
        if repo.head.is_detached:
            return None, None
        tracking = repo.active_branch.tracking_branch()
        if tracking is None:
            return None, None
        counts = repo.git.rev_list(
            "--left-right",
            "--count",
            f"{tracking.name}...{repo.active_branch.name}",
        ).strip()
        parts = counts.split("\t")
        if len(parts) != 2:
            return None, None
        behind = int(parts[0])
        ahead = int(parts[1])
        return ahead, behind
    except Exception:
        return None, None


def head_commit_age_days(repo: Repo) -> Optional[float]:
    """Return days elapsed since HEAD commit timestamp (committed datetime)."""
    try:
        commit = repo.head.commit
        authored = getattr(commit, "committed_datetime", None)
        if authored is None:
            return None
        if authored.tzinfo is None:
            authored = authored.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - authored.astimezone(timezone.utc)
        return round(delta.total_seconds() / 86400.0, 2)
    except Exception:
        return None


def merge_base_age_days(repo: Repo) -> Optional[float]:
    """
    Return days since merge-base(H, default remote branch) committed.

    Signals how stale the integration point with the remote default branch is.
    """
    try:
        head_ref = str(repo.head.commit.hexsha) if repo.head.is_detached else "HEAD"
        default_ref = _resolve_origin_default(repo=repo)
        if default_ref is None:
            return None
        bases = repo.git.merge_base(head_ref, default_ref).strip()
        if not bases:
            return None
        base_hex = bases.split()[0].strip()
        commit = repo.commit(base_hex)
        authored = getattr(commit, "committed_datetime", None)
        if authored is None:
            return None
        if authored.tzinfo is None:
            authored = authored.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - authored.astimezone(timezone.utc)
        return round(delta.total_seconds() / 86400.0, 2)
    except GitCommandError:
        return None
    except Exception:
        return None


def _resolve_origin_default(repo: Repo) -> Optional[str]:
    """Return ref like origin/main usable for merge-base, or None."""
    try:
        out = repo.git.symbolic_ref("refs/remotes/origin/HEAD").strip()
        if out.startswith("refs/remotes/"):
            return out[len("refs/remotes/") :].strip()
    except GitCommandError:
        pass
    for candidate in ("origin/main", "origin/master", "origin/develop"):
        try:
            repo.git.rev_parse("--verify", candidate)
            return candidate
        except GitCommandError:
            continue
    return None


def _uncommitted_count(repo: Repo, dirty: bool) -> int:
    """Estimate uncommitted change count."""
    if not dirty:
        return 0
    try:
        staged = len(repo.index.diff("HEAD"))
        unstaged = len(repo.index.diff(None))
        untracked = len(repo.untracked_files)
        return staged + unstaged + untracked
    except Exception:
        return 0
