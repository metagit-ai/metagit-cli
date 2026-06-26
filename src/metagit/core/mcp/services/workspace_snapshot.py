#!/usr/bin/env python
"""
Workspace snapshot create and restore for MCP tools.
"""

import contextlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.project_context import ProjectContextService
from metagit.core.mcp.services.repo_git_stats import inspect_repo_state
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.workspace.context_models import (
    SnapshotRepoState,
    WorkspaceSnapshot,
    WorkspaceSnapshotRestoreResult,
)


class WorkspaceSnapshotService:
    """Capture and restore workspace git-state manifests."""

    def __init__(
        self,
        index_service: Optional[WorkspaceIndexService] = None,
        context_service: Optional[ProjectContextService] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._context = context_service or ProjectContextService()

    def create(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        label: Optional[str] = None,
        project_name: Optional[str] = None,
        include_all_projects: bool = False,
        include_env_state: bool = True,
        link_session: bool = True,
    ) -> dict[str, Any]:
        """Create a snapshot manifest for scoped repositories."""
        store = SessionStore(workspace_root=workspace_root)
        meta = store.get_workspace_meta()
        active_project = project_name or meta.active_project
        rows = self._index.build_index(config=config, workspace_root=workspace_root)
        scoped_rows = (
            rows
            if include_all_projects
            else [row for row in rows if row["project_name"] == active_project]
            if active_project
            else rows
        )

        snapshot_id = str(uuid.uuid4())
        repo_states: list[SnapshotRepoState] = []
        for row in scoped_rows:
            repo_states.append(self._snapshot_repo_row(row=row))

        env_key_names: list[str] = []
        if include_env_state and active_project:
            env_key_names = self._context.list_env_export_keys(
                config=config,
                workspace_root=workspace_root,
                project_name=active_project,
            )

        session_ref = os.path.join(".metagit", "sessions", f"{active_project}.json") if active_project else None
        snapshot = WorkspaceSnapshot(
            snapshot_id=snapshot_id,
            active_project=active_project,
            label=label,
            repos=repo_states,
            env_key_names=env_key_names,
            session_ref=session_ref,
        )
        self._write_snapshot(workspace_root=workspace_root, snapshot=snapshot)
        if link_session:
            store.link_snapshot(snapshot_id=snapshot_id, project_name=active_project)
        return snapshot.model_dump(mode="json")

    def restore(
        self,
        config: MetagitConfig,
        workspace_root: str,
        snapshot_id: str,
        *,
        switch_project: bool = True,
        restore_session: bool = True,
    ) -> WorkspaceSnapshotRestoreResult:
        """Restore session metadata from a snapshot; does not mutate git state."""
        snapshot = self._load_snapshot(workspace_root=workspace_root, snapshot_id=snapshot_id)
        if snapshot is None:
            return WorkspaceSnapshotRestoreResult(
                ok=False,
                error="snapshot_not_found",
                snapshot_id=snapshot_id,
                notes=[
                    "Git branches, dirty state, and uncommitted changes were not modified.",
                ],
            )

        notes = [
            "Restore updated session metadata only.",
            "Git branches, dirty state, and uncommitted changes were not modified.",
        ]
        context = None
        if switch_project and snapshot.active_project:
            context = self._context.switch(
                config=config,
                workspace_root=workspace_root,
                project_name=snapshot.active_project,
                restore_session=restore_session,
                save_previous=True,
            )
        elif restore_session and snapshot.session_ref and snapshot.active_project:
            session_path = Path(workspace_root) / snapshot.session_ref
            self._restore_session_file(
                workspace_root=workspace_root,
                project_name=snapshot.active_project,
                session_path=session_path,
            )

        return WorkspaceSnapshotRestoreResult(
            ok=True,
            snapshot_id=snapshot_id,
            context=context,
            notes=notes,
        )

    def _snapshot_repo_row(self, row: dict[str, Any]) -> SnapshotRepoState:
        """Build snapshot repo state from an index row."""
        exists = bool(row.get("exists"))
        branch: Optional[str] = None
        dirty = False
        ahead: Optional[int] = None
        behind: Optional[int] = None
        uncommitted: Optional[int] = None
        inspect_error: Optional[str] = None
        if exists and row.get("is_git_repo"):
            inspected = inspect_repo_state(repo_path=str(row["repo_path"]))
            if inspected.get("ok"):
                branch = str(inspected["branch"]) if inspected.get("branch") else None
                dirty = bool(inspected.get("dirty", False))
                ahead_val = inspected.get("ahead")
                behind_val = inspected.get("behind")
                ahead = int(ahead_val) if isinstance(ahead_val, int) else None
                behind = int(behind_val) if isinstance(behind_val, int) else None
                uncommitted_val = inspected.get("uncommitted_count")
                uncommitted = int(uncommitted_val) if isinstance(uncommitted_val, int) else None
            else:
                inspect_error = str(inspected.get("error", "inspect failed"))
        return SnapshotRepoState(
            project_name=str(row.get("project_name", "")),
            repo_name=str(row.get("repo_name", "")),
            repo_path=str(row.get("repo_path", "")),
            branch=branch,
            dirty=dirty,
            ahead=ahead,
            behind=behind,
            uncommitted_count=uncommitted,
            inspect_error=inspect_error,
        )

    def _write_snapshot(self, workspace_root: str, snapshot: WorkspaceSnapshot) -> Path:
        """Write snapshot JSON to workspace .metagit/snapshots."""
        snapshots_dir = Path(workspace_root) / ".metagit" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        path = snapshots_dir / f"{snapshot.snapshot_id}.json"
        path.write_text(
            json.dumps(snapshot.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)
        return path

    def _load_snapshot(self, workspace_root: str, snapshot_id: str) -> Optional[WorkspaceSnapshot]:
        """Load snapshot by id."""
        path = Path(workspace_root) / ".metagit" / "snapshots" / f"{snapshot_id}.json"
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return WorkspaceSnapshot.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def _restore_session_file(
        self,
        workspace_root: str,
        project_name: str,
        session_path: Path,
    ) -> None:
        """Copy a snapshot-linked session file into the live session store."""
        if not session_path.is_file():
            return
        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        from metagit.core.workspace.context_models import ProjectSession

        store = SessionStore(workspace_root=workspace_root)
        session = ProjectSession.model_validate(payload)
        session.project_name = project_name
        store.save_project_session(session=session)
