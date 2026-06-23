#!/usr/bin/env python
"""
Persist workspace and per-project session state under a configurable sessions path.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

from metagit.core.workspace.context_models import (
    ProjectSession,
    WorkspaceSessionMeta,
    utc_now_iso,
    validate_env_key,
    validate_env_value,
)

_PROJECT_FILE_PATTERN = re.compile(r"^[\w.-]+$")


class SessionStore:
    """Read and write session JSON under the resolved workspace sessions directory."""

    def __init__(self, workspace_root: str, session_path: Optional[str] = None) -> None:
        self._workspace_root = str(Path(workspace_root).expanduser().resolve())
        resolved_session_path = (
            session_path
            or os.getenv("METAGIT_WORKSPACE_SESSION_PATH")
            or ".metagit/sessions"
        )
        candidate = Path(resolved_session_path).expanduser()
        self._sessions_dir = (
            candidate.resolve()
            if candidate.is_absolute()
            else (Path(self._workspace_root) / candidate).resolve()
        )
        self._workspace_meta_path = self._sessions_dir / "_workspace.json"

    @property
    def sessions_dir(self) -> Path:
        """Return the sessions directory path."""
        return self._sessions_dir

    def ensure_dirs(self) -> None:
        """Create session directories with restrictive permissions when possible."""
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self._sessions_dir, 0o700)
        except OSError:
            pass

    def get_workspace_meta(self) -> WorkspaceSessionMeta:
        """Load workspace session metadata or return defaults."""
        payload = self._read_json(path=self._workspace_meta_path)
        if not payload:
            return WorkspaceSessionMeta()
        return WorkspaceSessionMeta.model_validate(payload)

    def save_workspace_meta(self, meta: WorkspaceSessionMeta) -> None:
        """Persist workspace session metadata."""
        self.ensure_dirs()
        self._write_json(
            path=self._workspace_meta_path, payload=meta.model_dump(mode="json")
        )

    def set_active_project(self, project_name: str) -> WorkspaceSessionMeta:
        """Set active project on workspace metadata."""
        meta = self.get_workspace_meta()
        meta.active_project = project_name
        meta.last_switch_at = utc_now_iso()
        self.save_workspace_meta(meta=meta)
        return meta

    def get_project_session(self, project_name: str) -> ProjectSession:
        """Load a project session or return an empty session."""
        path = self._project_session_path(project_name=project_name)
        payload = self._read_json(path=path)
        if not payload:
            return ProjectSession(project_name=project_name)
        session = ProjectSession.model_validate(payload)
        session.project_name = project_name
        return session

    def save_project_session(self, session: ProjectSession) -> None:
        """Persist a project session."""
        self.ensure_dirs()
        session.updated_at = utc_now_iso()
        path = self._project_session_path(project_name=session.project_name)
        self._write_json(path=path, payload=session.model_dump(mode="json"))

    def update_project_session(
        self,
        project_name: str,
        *,
        recent_repos: Optional[list[str]] = None,
        primary_repo_path: Optional[str] = None,
        agent_notes: Optional[str] = None,
        env_overrides: Optional[dict[str, str]] = None,
        last_snapshot_id: Optional[str] = None,
    ) -> ProjectSession:
        """Merge updates into a project session."""
        session = self.get_project_session(project_name=project_name)
        if recent_repos is not None:
            session.recent_repos = recent_repos
        if primary_repo_path is not None:
            session.primary_repo_path = primary_repo_path
        if agent_notes is not None:
            session.agent_notes = agent_notes
        if env_overrides is not None:
            merged = dict(session.env_overrides)
            for key, value in env_overrides.items():
                merged[validate_env_key(key)] = validate_env_value(value)
            session.env_overrides = merged
        if last_snapshot_id is not None:
            session.last_snapshot_id = last_snapshot_id
        self.save_project_session(session=session)
        return session

    def rename_project_session(self, from_name: str, to_name: str) -> bool:
        """
        Rename a per-project session file when a workspace project is renamed.

        Returns True when a session file was migrated.
        """
        old_path = self._project_session_path(project_name=from_name)
        new_path = self._project_session_path(project_name=to_name)
        if not old_path.is_file():
            return False
        self.ensure_dirs()
        if new_path.exists():
            new_path.unlink()
        old_path.rename(new_path)
        session = self.get_project_session(project_name=to_name)
        session.project_name = to_name
        self.save_project_session(session=session)
        return True

    def link_snapshot(self, snapshot_id: str, project_name: Optional[str]) -> None:
        """Record snapshot id on workspace and optional project session."""
        meta = self.get_workspace_meta()
        meta.last_snapshot_id = snapshot_id
        self.save_workspace_meta(meta=meta)
        if project_name:
            self.update_project_session(
                project_name=project_name,
                last_snapshot_id=snapshot_id,
            )

    def touch_session(self) -> WorkspaceSessionMeta:
        """Record the current UTC time as the last session boundary."""
        meta = self.get_workspace_meta()
        meta.last_session_at = utc_now_iso()
        self.save_workspace_meta(meta=meta)
        return meta

    def get_last_session_at(self) -> Optional[str]:
        """Return last session timestamp or fall back to last project switch."""
        meta = self.get_workspace_meta()
        if meta.last_session_at:
            return meta.last_session_at
        return meta.last_switch_at

    def _project_session_path(self, project_name: str) -> Path:
        """Resolve sanitized per-project session file path."""
        if not _PROJECT_FILE_PATTERN.match(project_name):
            raise ValueError(f"Invalid project name for session file: {project_name}")
        return self._sessions_dir / f"{project_name}.json"

    def _read_json(self, path: Path) -> Optional[dict]:
        """Read JSON object from path."""
        if not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(self, path: Path, payload: dict) -> None:
        """Write JSON object to path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
