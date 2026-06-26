#!/usr/bin/env python
"""
GitNexus semantic workspace search (vector-ranked query per repository).
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Optional

from metagit.core.mcp.services.gitnexus_registry import GitNexusRegistryAdapter


class WorkspaceSemanticSearchService:
    """Run `gitnexus query` across workspace checkouts with a registry name."""

    _gitnexus_pkg = "gitnexus@1.6.4"

    def __init__(self, registry: Optional[GitNexusRegistryAdapter] = None) -> None:
        self._registry = registry or GitNexusRegistryAdapter()

    def search_across_repos(
        self,
        query: str,
        repo_paths: list[str],
        *,
        task_context: Optional[str] = None,
        goal: Optional[str] = None,
        limit_per_repo: int = 5,
        timeout_seconds: int = 120,
    ) -> dict[str, Any]:
        """Run semantic query for each indexed GitNexus repo path."""
        trimmed = query.strip()
        if not trimmed:
            return {"ok": False, "error": "empty_query", "results": []}

        results: list[dict[str, Any]] = []
        for repo_path in repo_paths:
            name = self._registry.registry_name_for_path(repo_path=repo_path)
            if not name:
                results.append(
                    {
                        "repo_path": repo_path,
                        "registry_name": None,
                        "ok": False,
                        "error": "not_in_gitnexus_registry",
                        "data": None,
                    }
                )
                continue
            payload, err = self._run_query(
                repo_path=repo_path,
                registry_name=name,
                query=trimmed,
                task_context=task_context,
                goal=goal,
                limit=limit_per_repo,
                timeout_seconds=timeout_seconds,
            )
            results.append(
                {
                    "repo_path": repo_path,
                    "registry_name": name,
                    "ok": err is None,
                    "error": err,
                    "data": payload,
                }
            )

        any_ok = any(item.get("ok") for item in results)
        return {
            "ok": any_ok,
            "query": trimmed,
            "results": results,
            "note": "Requires GitNexus index and optional embeddings; register repos with `gitnexus analyze`.",
        }

    def _run_query(
        self,
        repo_path: str,
        registry_name: str,
        query: str,
        task_context: Optional[str],
        goal: Optional[str],
        limit: int,
        timeout_seconds: int,
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """Execute gitnexus query and parse JSON payload from stdout."""
        cmd: list[str] = [
            "npx",
            "--yes",
            self._gitnexus_pkg,
            "query",
            "-r",
            registry_name,
            "-l",
            str(limit),
            query,
        ]
        if task_context:
            cmd.extend(["-c", task_context])
        if goal:
            cmd.extend(["-g", goal])
        try:
            completed = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=max(5, timeout_seconds),
            )
        except subprocess.TimeoutExpired:
            return None, "gitnexus query timed out"
        except OSError as exc:
            return None, str(exc)

        combined = (completed.stdout or "") + "\n" + (completed.stderr or "")
        payload = self._parse_query_json(stdout=combined)
        if payload is None:
            if completed.returncode != 0:
                return (
                    None,
                    f"gitnexus query exit {completed.returncode}: "
                    + (combined[:500] if combined.strip() else "no output"),
                )
            return None, "Could not parse gitnexus query JSON"

        warning = payload.get("warning") if isinstance(payload, dict) else None
        if warning and isinstance(warning, str) and completed.returncode != 0:
            return payload, warning
        return payload, None

    def _parse_query_json(self, stdout: str) -> Optional[dict[str, Any]]:
        """Extract the primary JSON object with processes from CLI output."""
        for line in stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            if '"processes"' not in line:
                continue
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict) and "processes" in decoded:
                return decoded
        return None
