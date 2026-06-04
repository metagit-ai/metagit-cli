#!/usr/bin/env python
"""
Tier-2 session digest: git activity per managed repo since a session boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError

from metagit.core.config.models import MetagitConfig
from metagit.core.context.models import SessionDigestRepoChange, SessionDigestResult
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService


def _parse_since_iso(value: str) -> datetime:
    """Parse an ISO-8601 boundary; treat naive values as UTC."""
    normalized = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _manifest_mtime_utc(config_path: str) -> Optional[datetime]:
    path = Path(config_path)
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


class SessionDigestService:
    """Build ``SessionDigestResult`` from workspace index rows and git history."""

    @staticmethod
    def build(
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        *,
        since: Optional[str] = None,
        active_objective_id: Optional[str] = None,
        definition_root: Optional[str] = None,
    ) -> SessionDigestResult:
        """
        Assemble a session digest.

        When ``since`` is omitted, this is treated as a first session: no git
        queries and an empty ``repo_changes`` list.
        """
        if since is None:
            return SessionDigestResult(
                since=None,
                first_session=True,
                manifest_changed=False,
                active_objective_id=active_objective_id,
                repo_changes=[],
            )

        since_dt = _parse_since_iso(since)
        manifest_mtime = _manifest_mtime_utc(config_path)
        manifest_changed = bool(
            manifest_mtime is not None and manifest_mtime > since_dt
        )

        index = WorkspaceIndexService()
        resolved_definition_root = definition_root or str(
            Path(config_path).expanduser().resolve().parent
        )
        repo_changes: list[SessionDigestRepoChange] = []
        for row in index.build_index(
            config,
            workspace_root,
            definition_root=resolved_definition_root,
        ):
            if not row.get("exists") or not row.get("is_git_repo"):
                continue
            repo_path = str(row["repo_path"])
            change = SessionDigestService._repo_digest_row(
                project_name=str(row["project_name"]),
                repo_name=str(row["repo_name"]),
                repo_path=repo_path,
                since=since,
            )
            repo_changes.append(change)

        return SessionDigestResult(
            since=since,
            first_session=False,
            manifest_changed=manifest_changed,
            active_objective_id=active_objective_id,
            repo_changes=repo_changes,
        )

    @staticmethod
    def _repo_digest_row(
        *,
        project_name: str,
        repo_name: str,
        repo_path: str,
        since: str,
    ) -> SessionDigestRepoChange:
        try:
            repo = Repo(repo_path)
            count_raw = repo.git.rev_list(
                "--count",
                "HEAD",
                f"--since={since}",
            ).strip()
            commit_count = int(count_raw)
            log_out = repo.git.log(
                f"--since={since}",
                "--oneline",
                "-n",
                "3",
            )
            lines = [ln.strip() for ln in log_out.splitlines() if ln.strip()][:3]
            return SessionDigestRepoChange(
                project_name=project_name,
                repo_name=repo_name,
                repo_path=repo_path,
                commit_count=commit_count,
                recent_subjects=lines,
            )
        except GitCommandError as exc:
            return SessionDigestRepoChange(
                project_name=project_name,
                repo_name=repo_name,
                repo_path=repo_path,
                commit_count=0,
                recent_subjects=[],
                error=str(exc),
            )
        except (OSError, ValueError) as exc:
            return SessionDigestRepoChange(
                project_name=project_name,
                repo_name=repo_name,
                repo_path=repo_path,
                commit_count=0,
                recent_subjects=[],
                error=str(exc),
            )


__all__ = ["SessionDigestService"]
