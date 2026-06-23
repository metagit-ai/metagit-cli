#!/usr/bin/env python
"""Incremental workspace events feed with timestamp cursor filtering."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.handoff_service import HandoffService
from metagit.core.context.models import WorkspaceEvent, WorkspaceEventsResult
from metagit.core.context.objective_service import ObjectiveService


class WorkspaceEventService:
    """Build a lightweight event timeline for polling orchestrators."""

    def __init__(self, workspace_root: str) -> None:
        self._root = str(Path(workspace_root).expanduser().resolve())

    def list_events(self, *, since: Optional[str] = None) -> WorkspaceEventsResult:
        rows: list[WorkspaceEvent] = []

        for item in ObjectiveService(workspace_root=self._root).list().objectives:
            rows.append(
                WorkspaceEvent(
                    timestamp=item.updated_at,
                    source="objective",
                    kind=item.status,
                    id=item.id,
                    data={"title": item.title, "repos": list(item.repos)},
                )
            )

        for req in ApprovalService(workspace_root=self._root).list(status=None).requests:
            rows.append(
                WorkspaceEvent(
                    timestamp=req.resolved_at or req.created_at,
                    source="approval",
                    kind=req.status,
                    id=req.id,
                    data={"action": req.action, "requested_by": req.requested_by},
                )
            )

        for handoff in HandoffService(workspace_root=self._root).list().handoffs:
            rows.append(
                WorkspaceEvent(
                    timestamp=handoff.updated_at,
                    source="handoff",
                    kind=handoff.status,
                    id=handoff.id,
                    data={"title": handoff.title, "claimed_by": handoff.claimed_by},
                )
            )

        snapshots_dir = Path(self._root) / ".metagit" / "snapshots"
        if snapshots_dir.is_dir():
            for path in snapshots_dir.glob("*.json"):
                stat = path.stat()
                ts = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                rows.append(
                    WorkspaceEvent(
                        timestamp=ts,
                        source="snapshot",
                        kind="created",
                        id=path.stem,
                        data={"path": str(path), "mtime": stat.st_mtime},
                    )
                )

        rows.sort(key=lambda item: item.timestamp)
        if since:
            rows = [row for row in rows if row.timestamp > since]
        next_cursor = rows[-1].timestamp if rows else since
        return WorkspaceEventsResult(since=since, next_cursor=next_cursor, events=rows)
