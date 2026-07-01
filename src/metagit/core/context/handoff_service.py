#!/usr/bin/env python
"""First-class handoff service for multi-agent coordination."""

from __future__ import annotations

import uuid
from typing import Optional

from metagit.core.context.handoff_store import HandoffStore
from metagit.core.context.models import HandoffEvent, HandoffItem, HandoffListResult
from metagit.core.state.retry import with_state_retry
from metagit.core.workspace.context_models import utc_now_iso


class HandoffService:
    """Create, claim, complete, and list handoffs."""

    def __init__(self, workspace_root: str) -> None:
        self._store = HandoffStore(workspace_root=workspace_root)

    def list(self, status: Optional[str] = None) -> HandoffListResult:
        rows = self._store.load_handoffs()
        if status:
            rows = [row for row in rows if row.status == status]
        return HandoffListResult(handoffs=rows)

    def create(
        self,
        *,
        title: str,
        created_by: str,
        payload: Optional[dict] = None,
    ) -> HandoffItem:
        now = utc_now_iso()
        row = HandoffItem(
            id=uuid.uuid4().hex,
            title=title.strip(),
            created_by=created_by.strip() or "agent",
            payload=dict(payload or {}),
            created_at=now,
            updated_at=now,
            events=[
                HandoffEvent(
                    at=now,
                    by=created_by.strip() or "agent",
                    action="create",
                )
            ],
        )
        return self._store.append_handoff(row)

    def claim(self, handoff_id: str, *, claimed_by: str, note: Optional[str]) -> HandoffItem:
        return self._transition(
            handoff_id,
            to_status="claimed",
            actor=claimed_by,
            action="claim",
            note=note,
            claimed_by=claimed_by,
        )

    def complete(self, handoff_id: str, *, actor: str, note: Optional[str]) -> HandoffItem:
        return self._transition(
            handoff_id,
            to_status="completed",
            actor=actor,
            action="complete",
            note=note,
            claimed_by=None,
        )

    def _transition(
        self,
        handoff_id: str,
        *,
        to_status: str,
        actor: str,
        action: str,
        note: Optional[str],
        claimed_by: Optional[str],
    ) -> HandoffItem:
        def _run() -> HandoffItem:
            rows = self._store.load_handoffs()
            idx = next((i for i, row in enumerate(rows) if row.id == handoff_id), None)
            if idx is None:
                raise ValueError(f"handoff not found: {handoff_id}")
            now = utc_now_iso()
            row = rows[idx]
            events = list(row.events)
            events.append(
                HandoffEvent(
                    at=now,
                    by=actor.strip() or "agent",
                    action=action,
                    note=note,
                )
            )
            updated = row.model_copy(
                update={
                    "status": to_status,
                    "claimed_by": claimed_by if claimed_by is not None else row.claimed_by,
                    "updated_at": now,
                    "events": events,
                }
            )
            rows[idx] = updated
            self._store.save_handoffs(rows)
            return updated

        return with_state_retry(_run)
