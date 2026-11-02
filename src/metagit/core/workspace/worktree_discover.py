#!/usr/bin/env python
"""Find and clean git worktrees in synced workspace repositories."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

from metagit.manifest import load_composed

PullRequestLookup = Callable[[str, str, str], dict[str, str] | None]


def discover_worktrees(
    manifest: Path,
    *,
    pr_lookup: PullRequestLookup | None = None,
    include_pr: bool = False,
) -> list[dict[str, Any]]:
    """Return every git worktree under synced repositories, including the primary checkout."""
    records: list[dict[str, Any]] = []
    for repo_name, checkout in _synced_checkouts(manifest):
        for worktree in _git_worktrees(checkout):
            path = Path(worktree["path"])
            branch = worktree.get("branch")
            record: dict[str, Any] = {
                "repo": repo_name,
                "path": str(path),
                "branch": branch,
                "dirty": _is_dirty(path),
                "ahead": _commits_ahead(path),
                "primary": path.resolve() == checkout.resolve(),
                "checkout": str(checkout.resolve()),
                "pr": None,
            }
            if include_pr and pr_lookup is not None and branch:
                remote = _remote_url(checkout)
                record["pr"] = pr_lookup(repo_name, remote or "", branch)
            records.append(record)
    return records


def gc_merged_worktrees(
    manifest: Path,
    *,
    dry_run: bool,
    pr_lookup: PullRequestLookup | None = None,
) -> dict[str, Any]:
    """Remove clean worktrees whose HEAD is the head of a merged or closed pull request.

    Dirty trees and the primary checkout are skipped. Removal never uses
    ``git worktree remove --force``.
    """
    lookup = pr_lookup or default_pr_lookup
    remove: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for record in discover_worktrees(manifest, pr_lookup=lookup, include_pr=True):
        reason = _skip_reason(record)
        if reason is not None:
            skipped.append({"path": record["path"], "reason": reason})
            continue
        remove.append(record)
        if not dry_run:
            _remove_worktree(Path(str(record["checkout"])), Path(str(record["path"])))
    return {"dry_run": dry_run, "remove": remove, "skipped": skipped}


def default_pr_lookup(repo_name: str, remote_url: str, branch: str) -> dict[str, str] | None:
    """Look up a pull request when a GitHub token is set. Otherwise return None."""
    _ = repo_name
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token or not remote_url or not branch:
        return None
    slug = _github_slug(remote_url)
    if slug is None:
        return None
    try:
        url = f"https://api.github.com/repos/{slug}/pulls?head={slug.split('/')[0]}:{branch}&state=all&per_page=5"
        request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    pull = payload[0]
    state = "merged" if pull.get("merged_at") else str(pull.get("state") or "")
    head = pull.get("head") if isinstance(pull.get("head"), dict) else {}
    sha = str(head.get("sha") or "")
    if state not in {"merged", "closed", "open"} or not sha:
        return None
    return {"state": state, "head_sha": sha}


def _synced_checkouts(manifest: Path) -> list[tuple[str, Path]]:
    root = manifest.expanduser().resolve().parent
    data = load_composed(manifest)
    workspace = data.get("workspace") if isinstance(data.get("workspace"), dict) else {}
    found: list[tuple[str, Path]] = []
    for project in workspace.get("projects") or []:
        if not isinstance(project, dict) or not project.get("name"):
            continue
        for repo in project.get("repos") or []:
            if not isinstance(repo, dict) or not repo.get("name") or repo.get("sync") is False:
                continue
            raw = repo.get("path")
            if raw:
                candidate = Path(str(raw)).expanduser()
                if not candidate.is_absolute():
                    candidate = root / candidate
            else:
                candidate = root / str(project["name"]) / str(repo["name"])
            if (candidate / ".git").is_dir():
                found.append((f"{project['name']}/{repo['name']}", candidate.resolve()))
    return found


def _git_worktrees(checkout: Path) -> list[dict[str, str]]:
    completed = _git(checkout, "worktree", "list", "--porcelain")
    if completed.returncode != 0:
        return []
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if not line.strip():
            if current.get("path"):
                records.append(current)
            current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            ref = line.split(" ", 1)[1]
            current["branch"] = ref.removeprefix("refs/heads/")
        elif line.startswith("HEAD "):
            current["head"] = line.split(" ", 1)[1]
    if current.get("path"):
        records.append(current)
    return records


def _is_dirty(path: Path) -> bool:
    completed = _git(path, "status", "--porcelain")
    return bool(completed.stdout.strip())


def _commits_ahead(path: Path) -> int | None:
    completed = _git(path, "rev-list", "--count", "@{upstream}..HEAD")
    if completed.returncode != 0:
        return None
    try:
        return int(completed.stdout.strip())
    except ValueError:
        return None


def _remote_url(checkout: Path) -> str | None:
    completed = _git(checkout, "remote", "get-url", "origin")
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _head(path: Path) -> str:
    completed = _git(path, "rev-parse", "HEAD")
    return completed.stdout.strip()


def _skip_reason(record: dict[str, Any]) -> str | None:
    if record.get("primary"):
        return "primary checkout"
    if record.get("dirty"):
        return "dirty"
    pull = record.get("pr")
    if not isinstance(pull, dict):
        return "no pull request"
    state = str(pull.get("state") or "")
    if state not in {"merged", "closed"}:
        return f"pull request is {state or 'unknown'}"
    head = _head(Path(str(record["path"])))
    if head != str(pull.get("head_sha") or ""):
        return "HEAD is not the pull request head"
    return None


def _remove_worktree(checkout: Path, path: Path) -> None:
    completed = _git(checkout, "worktree", "remove", str(path))
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"could not remove worktree {path}")


def _github_slug(remote_url: str) -> str | None:
    text = remote_url[:-4] if remote_url.endswith(".git") else remote_url
    if "github.com" not in text.lower():
        return None
    if ":" in text and "github.com:" in text:
        path = text.split("github.com:", 1)[1]
    else:
        marker = text.lower().find("github.com/")
        if marker < 0:
            return None
        path = text[marker + len("github.com/") :]
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    return f"{parts[-2]}/{parts[-1]}"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=False,
        capture_output=True,
        text=True,
    )
