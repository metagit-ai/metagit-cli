#!/usr/bin/env python
"""Find and clean git worktrees in synced workspace repositories."""

from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from metagit.core.workspace.root_resolver import resolve_sync_root
from metagit.core.workspace.workspace_dedupe import project_mount_path
from metagit.manifest import load_composed

PullRequestLookup = Callable[[str, str, str], dict[str, str] | None]


def discover_worktrees(
    manifest: Path,
    *,
    pr_lookup: PullRequestLookup | None = None,
    include_pr: bool = False,
    workspace_path: str | None = None,
) -> list[dict[str, Any]]:
    """Return every git worktree under synced repositories, including the primary checkout."""
    records: list[dict[str, Any]] = []
    for repo_name, checkout, manifest_url in _synced_checkouts(manifest, workspace_path=workspace_path):
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
                "pr_reason": None,
            }
            if include_pr and pr_lookup is not None and branch:
                remote = _remote_url(checkout)
                outcome = _invoke_pr_lookup(pr_lookup, repo_name, remote or "", branch, manifest_url)
                if isinstance(outcome, dict) and outcome.get("state"):
                    record["pr"] = outcome
                elif isinstance(outcome, dict) and outcome.get("reason"):
                    record["pr_reason"] = str(outcome["reason"])
                else:
                    record["pr_reason"] = "no pull request"
            records.append(record)
    return records


def gc_merged_worktrees(
    manifest: Path,
    *,
    dry_run: bool,
    pr_lookup: PullRequestLookup | None = None,
    workspace_path: str | None = None,
) -> dict[str, Any]:
    """Remove clean worktrees whose HEAD is the head of a merged or closed pull request.

    Dirty trees and the primary checkout are skipped. Removal never uses
    ``git worktree remove --force``.
    """
    lookup = pr_lookup or default_pr_lookup
    remove: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for record in discover_worktrees(
        manifest,
        pr_lookup=lookup,
        include_pr=True,
        workspace_path=workspace_path,
    ):
        reason = _skip_reason(record)
        if reason is not None:
            skipped.append({"path": record["path"], "reason": reason})
            continue
        remove.append(record)
        if not dry_run:
            _remove_worktree(Path(str(record["checkout"])), Path(str(record["path"])))
    return {"dry_run": dry_run, "remove": remove, "skipped": skipped}


def default_pr_lookup(
    repo_name: str,
    remote_url: str,
    branch: str,
    manifest_url: str | None = None,
) -> dict[str, str] | None:
    """Look up a pull request when a GitHub token is set.

    The manifest repo ``url`` is the canonical address. The checkout remote is
    the fallback, and an SSH host alias is resolved with ``ssh -G``. A miss is
    ``no pull request``, ``forge not supported``, or ``lookup failed``.
    """
    _ = repo_name
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token or not branch:
        return None
    if not remote_url and not manifest_url:
        return {"reason": "no pull request"}
    slug, failure = _github_slug_from(manifest_url, remote_url)
    if failure:
        return {"reason": failure}
    if slug is None:
        return {"reason": "no pull request"}
    query = f"repos/{slug}/pulls?head={slug.split('/')[0]}:{branch}&state=all&per_page=5"
    completed = subprocess.run(
        ["gh", "api", query],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "GH_TOKEN": token},
    )
    if completed.returncode != 0:
        return {"reason": "lookup failed"}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"reason": "lookup failed"}
    if not isinstance(payload, list) or not payload:
        return {"reason": "no pull request"}
    pull = payload[0]
    state = "merged" if pull.get("merged_at") else str(pull.get("state") or "")
    head = pull.get("head") if isinstance(pull.get("head"), dict) else {}
    sha = str(head.get("sha") or "")
    if state not in {"merged", "closed", "open"} or not sha:
        return None
    return {"state": state, "head_sha": sha}


def _synced_checkouts(
    manifest: Path,
    *,
    workspace_path: str | None = None,
) -> list[tuple[str, Path, str | None]]:
    """Return synced checkouts at the same paths ``project sync`` clones into.

    An explicit repo ``path`` is that checkout. Otherwise the repo lives under
    the workspace path (``METAGIT_WORKSPACE_PATH`` or app config, default
    ``./.metagit`` relative to the manifest).
    """
    root = manifest.expanduser().resolve().parent
    sync_root = Path(_sync_root(root, workspace_path))
    data = load_composed(manifest)
    workspace = data.get("workspace") if isinstance(data.get("workspace"), dict) else {}
    found: list[tuple[str, Path]] = []
    for project in workspace.get("projects") or []:
        if not isinstance(project, dict) or not project.get("name"):
            continue
        for repo in project.get("repos") or []:
            if not isinstance(repo, dict) or not repo.get("name") or repo.get("sync") is False:
                continue
            candidate = _checkout_path(
                root,
                sync_root,
                project_name=str(project["name"]),
                repo_name=str(repo["name"]),
                configured_path=str(repo["path"]) if repo.get("path") else None,
            )
            if (candidate / ".git").exists():
                url = str(repo.get("url") or "") or None
                found.append((f"{project['name']}/{repo['name']}", candidate.resolve(), url))
    return found


def _sync_root(definition_root: Path, workspace_path: str | None) -> str:
    configured = workspace_path or os.environ.get("METAGIT_WORKSPACE_PATH") or "./.metagit"
    return resolve_sync_root(str(definition_root), configured)


def _checkout_path(
    definition_root: Path,
    sync_root: Path,
    *,
    project_name: str,
    repo_name: str,
    configured_path: str | None,
) -> Path:
    if configured_path:
        candidate = Path(configured_path).expanduser()
        if candidate.is_absolute():
            return candidate
        return definition_root / candidate
    return project_mount_path(sync_root, project_name, repo_name)


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
        reason = record.get("pr_reason")
        return str(reason) if reason else "no pull request"
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


def _invoke_pr_lookup(
    lookup: PullRequestLookup,
    repo_name: str,
    remote_url: str,
    branch: str,
    manifest_url: str | None,
) -> dict[str, str] | None:
    """Pass the manifest URL when the lookup accepts it."""
    try:
        parameters = inspect.signature(lookup).parameters
    except (TypeError, ValueError):
        parameters = {}
    if "manifest_url" in parameters:
        return lookup(repo_name, remote_url, branch, manifest_url=manifest_url)  # type: ignore[call-arg]
    return lookup(repo_name, remote_url, branch)


def _github_slug_from(manifest_url: str | None, remote_url: str | None) -> tuple[str | None, str | None]:
    """Return ``(owner/repo, failure)``. Prefer the manifest URL."""
    saw_other = False
    failed = False
    for candidate in (manifest_url, remote_url):
        if not candidate:
            continue
        parsed = _parse_git_remote(candidate)
        if parsed is None:
            continue
        host, path = parsed
        hostname, error = _canonical_hostname(host)
        if error:
            failed = True
            continue
        if hostname == "github.com":
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1]}", None
            continue
        saw_other = True
    if saw_other:
        return None, "forge not supported"
    if failed:
        return None, "lookup failed"
    return None, None


def _parse_git_remote(url: str) -> tuple[str, str] | None:
    text = url.strip()
    if text.lower().endswith(".git"):
        text = text[: -len(".git")]
    if "://" in text:
        parsed = urlparse(text)
        if parsed.hostname and parsed.path:
            return parsed.hostname, parsed.path.strip("/")
        return None
    match = re.match(r"^(?:ssh://)?(?:[^@/]+@)?(?P<host>[^:/]+)[:/](?P<path>.+)$", text)
    if not match:
        return None
    return match.group("host"), match.group("path").strip("/")


def _canonical_hostname(host: str) -> tuple[str | None, str | None]:
    """Return ``(hostname, error)``. Aliases without a dot go through ``ssh -G``."""
    lowered = host.lower().rstrip(".")
    if lowered in {"github.com", "www.github.com", "ssh.github.com"}:
        return "github.com", None
    if "." in lowered:
        return lowered, None
    completed = subprocess.run(
        ["ssh", "-G", host],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None, "lookup failed"
    hostname = ""
    for line in completed.stdout.splitlines():
        if line.startswith("hostname "):
            hostname = line.split(None, 1)[1].strip()
            break
    if not hostname:
        return None, "lookup failed"
    return hostname.lower(), None


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=False,
        capture_output=True,
        text=True,
    )
