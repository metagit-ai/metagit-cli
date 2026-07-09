#!/usr/bin/env python
"""Incremental workspace events feed with timestamp cursor filtering."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.handoff_service import HandoffService
from metagit.core.context.models import WorkspaceEvent, WorkspaceEventsResult
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.coordination.event_store import AclEventStore
from metagit.core.semantic.events import SemanticGraphEventStore
from metagit.core.taskgraph.events import TaskGraphEventStore


class WorkspaceEventService:
    """Build a lightweight event timeline for polling orchestrators."""

    def __init__(self, workspace_root: str) -> None:
        self._root = str(Path(workspace_root).expanduser().resolve())

    def list_events(
        self,
        *,
        since: Optional[str] = None,
        campaign: Optional[str] = None,
        objective_id: Optional[str] = None,
    ) -> WorkspaceEventsResult:
        rows: list[WorkspaceEvent] = []

        for item in ObjectiveService(workspace_root=self._root).list().objectives:
            if objective_id and item.id != objective_id:
                continue
            if campaign and not item.id.startswith(f"campaign-{campaign}-"):
                continue
            rows.append(
                WorkspaceEvent(
                    timestamp=item.updated_at,
                    source="objective",
                    kind=item.status,
                    id=item.id,
                    data={
                        "title": item.title,
                        "repos": list(item.repos),
                        "mr_url": item.mr_url,
                        "approval_id": item.approval_id,
                    },
                )
            )

        for req in ApprovalService(workspace_root=self._root).list(status=None).requests:
            if objective_id and req.payload.get("objective_id") != objective_id:
                continue
            if campaign and req.payload.get("campaign") != campaign:
                continue
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
            if objective_id and handoff.payload.get("objective_id") != objective_id:
                continue
            if campaign and handoff.payload.get("campaign") != campaign:
                continue
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

        acl_events = AclEventStore(self._root).list_events(since=None)
        if not isinstance(acl_events, Exception):
            for event in acl_events:
                if objective_id and event.payload.get("objective_id") != objective_id:
                    continue
                if campaign and event.payload.get("campaign") != campaign:
                    continue
                rows.append(
                    WorkspaceEvent(
                        timestamp=event.at,
                        source="acl",
                        kind=event.type,
                        id=event.event_id,
                        data=dict(event.payload),
                    )
                )

        task_events = TaskGraphEventStore(self._root).list_events(since=None)
        if not isinstance(task_events, Exception):
            for event in task_events:
                if objective_id and event.payload.get("objective_id") != objective_id:
                    continue
                if campaign and event.payload.get("campaign") != campaign:
                    continue
                rows.append(
                    WorkspaceEvent(
                        timestamp=event.at,
                        source="taskgraph",
                        kind=event.type,
                        id=event.event_id,
                        data=dict(event.payload),
                    )
                )

        semantic_events = SemanticGraphEventStore(self._root).list_events(since=None)
        if not isinstance(semantic_events, Exception):
            for event in semantic_events:
                if objective_id and event.payload.get("objective_id") != objective_id:
                    continue
                if campaign and event.payload.get("campaign") != campaign:
                    continue
                rows.append(
                    WorkspaceEvent(
                        timestamp=event.at,
                        source="semantic",
                        kind=event.type,
                        id=event.event_id,
                        data=dict(event.payload),
                    )
                )

        context_events_path = Path(self._root) / ".metagit" / "events" / "context.jsonl"
        if context_events_path.is_file():
            for line in context_events_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    raw = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if not isinstance(raw, dict):
                    continue
                payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
                if objective_id and payload.get("objective_id") != objective_id:
                    continue
                if campaign and payload.get("campaign") != campaign:
                    continue
                rows.append(
                    WorkspaceEvent(
                        timestamp=str(raw.get("at") or ""),
                        source="context",
                        kind=str(raw.get("type") or "ContextCompiled"),
                        id=str(raw.get("event_id") or ""),
                        data=dict(payload),
                    )
                )

        rows.sort(key=lambda item: item.timestamp)
        if since:
            rows = [row for row in rows if row.timestamp > since]
        next_cursor = rows[-1].timestamp if rows else since
        return WorkspaceEventsResult(since=since, next_cursor=next_cursor, events=rows)
