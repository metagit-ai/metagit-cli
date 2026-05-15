#!/usr/bin/env python
"""
Batch workspace repository synchronization for MCP tools.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

from metagit.core.mcp.services.repo_git_stats import inspect_repo_state
from metagit.core.mcp.services.repo_ops import RepoOperationsService


class WorkspaceSyncService:
    """Synchronize many workspace repositories with guardrails."""

    def __init__(self, repo_ops: Optional[RepoOperationsService] = None) -> None:
        self._repo_ops = repo_ops or RepoOperationsService()

    def sync_many(
        self,
        repo_rows: list[dict[str, Any]],
        *,
        repos: Optional[list[str]] = None,
        mode: str = "fetch",
        only_if: str = "any",
        allow_mutation: bool = False,
        max_parallel: int = 4,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Sync selected repositories and return per-repo results."""
        selected_rows = self._select_rows(repo_rows=repo_rows, repos=repos)
        normalized_mode = mode.lower()
        normalized_only_if = only_if.lower()
        if normalized_mode not in {"fetch", "pull", "clone"}:
            return {
                "ok": False,
                "error": "Unsupported sync mode.",
                "results": [],
                "summary": {},
            }
        parallel = max(1, min(max_parallel, 16))
        results: list[dict[str, Any]] = []

        def run_row(row: dict[str, Any]) -> dict[str, Any]:
            return self._sync_row(
                row=row,
                mode=normalized_mode,
                only_if=normalized_only_if,
                allow_mutation=allow_mutation,
                dry_run=dry_run,
            )

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {executor.submit(run_row, row): row for row in selected_rows}
            for future in as_completed(futures):
                results.append(future.result())

        results.sort(
            key=lambda item: (item.get("project_name", ""), item.get("repo_name", ""))
        )
        summary = {
            "total": len(results),
            "ok": sum(1 for item in results if item.get("ok")),
            "skipped": sum(1 for item in results if item.get("skipped")),
            "failed": sum(
                1 for item in results if not item.get("ok") and not item.get("skipped")
            ),
            "dry_run": dry_run,
        }
        return {"ok": summary["failed"] == 0, "results": results, "summary": summary}

    def _select_rows(
        self,
        repo_rows: list[dict[str, Any]],
        repos: Optional[list[str]],
    ) -> list[dict[str, Any]]:
        """Filter index rows by repo selectors."""
        if not repos or repos == ["all"]:
            return list(repo_rows)
        selectors = {item.strip() for item in repos if item.strip()}
        selected: list[dict[str, Any]] = []
        for row in repo_rows:
            repo_path = str(row.get("repo_path", ""))
            repo_name = str(row.get("repo_name", ""))
            project_name = str(row.get("project_name", ""))
            keys = {repo_path, repo_name, f"{project_name}/{repo_name}"}
            if selectors.intersection(keys):
                selected.append(row)
        return selected

    def _sync_row(
        self,
        row: dict[str, Any],
        mode: str,
        only_if: str,
        allow_mutation: bool,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Sync one repository row."""
        base = {
            "project_name": row.get("project_name"),
            "repo_name": row.get("repo_name"),
            "repo_path": row.get("repo_path"),
            "ok": False,
            "skipped": False,
            "mode": mode,
        }
        repo_path = str(row.get("repo_path", ""))
        exists = bool(row.get("exists"))
        is_git_repo = bool(row.get("is_git_repo"))
        should_sync, skip_reason = self._should_sync(
            repo_path=repo_path,
            exists=exists,
            is_git_repo=is_git_repo,
            only_if=only_if,
        )
        if not should_sync:
            base["skipped"] = True
            base["skipped_reason"] = skip_reason
            base["ok"] = True
            return base
        if dry_run:
            base["ok"] = True
            base["dry_run"] = True
            return base
        origin_url = str(row.get("url")) if row.get("url") else None
        if mode == "clone" and not exists and not origin_url:
            base["error"] = "origin_url is required for clone mode."
            return base
        outcome = self._repo_ops.sync(
            repo_path=repo_path,
            mode=mode,
            allow_mutation=allow_mutation,
            origin_url=origin_url,
        )
        base.update(outcome)
        return base

    def _should_sync(
        self,
        repo_path: str,
        exists: bool,
        is_git_repo: bool,
        only_if: str,
    ) -> tuple[bool, Optional[str]]:
        """Determine whether a repository should be synchronized."""
        if only_if == "any":
            return True, None
        if only_if == "missing":
            if exists and is_git_repo:
                return False, "already_present"
            return True, None
        if only_if == "dirty":
            if not exists or not is_git_repo:
                return False, "not_a_git_repo"
            inspected = inspect_repo_state(repo_path=repo_path)
            if inspected.get("ok") and inspected.get("dirty"):
                return True, None
            return False, "clean"
        if only_if == "behind_origin":
            if not exists or not is_git_repo:
                return False, "not_a_git_repo"
            inspected = inspect_repo_state(repo_path=repo_path)
            behind = inspected.get("behind")
            if inspected.get("ok") and isinstance(behind, int) and behind > 0:
                return True, None
            return False, "not_behind_origin"
        return True, None
