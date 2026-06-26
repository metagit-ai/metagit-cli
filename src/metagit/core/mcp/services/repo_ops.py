#!/usr/bin/env python
"""
Repository inspection and guarded synchronization operations.
"""

import os
from typing import Optional

from git import Repo


class RepoOperationsService:
    """Provide safe repo inspect/sync operations for MCP tools."""

    def inspect(self, repo_path: str) -> dict[str, str | bool]:
        """Inspect repository branch and dirty state."""
        if not os.path.isdir(repo_path):
            return {"ok": False, "error": "Repository path does not exist."}
        try:
            repo = Repo(repo_path)
            return {
                "ok": True,
                "branch": str(repo.active_branch.name) if not repo.head.is_detached else "DETACHED",
                "dirty": repo.is_dirty(untracked_files=True),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def sync(
        self,
        repo_path: str,
        mode: str = "fetch",
        allow_mutation: bool = False,
        origin_url: Optional[str] = None,
    ) -> dict[str, str | bool]:
        """Synchronize repository with mutation guardrails."""
        normalized_mode = mode.lower()
        if normalized_mode not in {"fetch", "pull", "clone"}:
            return {"ok": False, "error": "Unsupported sync mode."}

        if normalized_mode in {"pull", "clone"} and not allow_mutation:
            return {
                "ok": False,
                "error": "Mutation disabled for pull/clone operations.",
            }

        try:
            if normalized_mode == "clone":
                if not origin_url:
                    return {
                        "ok": False,
                        "error": "origin_url is required for clone mode.",
                    }
                Repo.clone_from(origin_url, repo_path)
                return {"ok": True, "mode": "clone"}

            repo = Repo(repo_path)
            origin = repo.remote(name="origin")
            if normalized_mode == "fetch":
                origin.fetch()
                return {"ok": True, "mode": "fetch"}

            origin.pull()
            return {"ok": True, "mode": "pull"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
