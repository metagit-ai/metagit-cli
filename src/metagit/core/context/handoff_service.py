#!/usr/bin/env python
"""First-class handoff service for multi-agent coordination."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from metagit.core.context.handoff_store import HandoffStore
from metagit.core.context.models import HandoffEvent, HandoffItem, HandoffListResult
from metagit.core.state.retry import with_state_retry
from metagit.core.workspace.context_models import utc_now_iso

_TTL_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd])?$")


def parse_ttl_seconds(ttl: str) -> int:
    """Parse duration strings like 300, 30m, 2h, 1d into seconds."""
    normalized = ttl.strip().lower()
    match = _TTL_PATTERN.match(normalized)
    if not match:
        raise ValueError(f"invalid ttl {ttl!r}; use seconds or suffix s/m/h/d")
    value = int(match.group("value"))
    unit = match.group("unit") or "s"
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return value * multiplier


class HandoffService:
    """Create, claim, complete, and list handoffs."""

    def __init__(self, workspace_root: str) -> None:
        self._store = HandoffStore(workspace_root=workspace_root)

    def list(self, status: Optional[str] = None) -> HandoffListResult:
        rows = self._release_expired_claims(self._store.load_handoffs())
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

    def claim(
        self,
        handoff_id: str,
        *,
        claimed_by: str,
        note: Optional[str],
        ttl: Optional[str] = None,
    ) -> HandoffItem:
        expires_at: Optional[str] = None
        if ttl:
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=parse_ttl_seconds(ttl))).isoformat()
        return self._transition(
            handoff_id,
            to_status="claimed",
            actor=claimed_by,
            action="claim",
            note=note,
            claimed_by=claimed_by,
            claim_expires_at=expires_at,
            last_heartbeat_at=utc_now_iso(),
        )

    def heartbeat(self, handoff_id: str, *, actor: str, ttl: Optional[str] = None) -> HandoffItem:
        expires_at: Optional[str] = None
        if ttl:
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=parse_ttl_seconds(ttl))).isoformat()
        return self._transition(
            handoff_id,
            to_status="claimed",
            actor=actor,
            action="heartbeat",
            note=None,
            claimed_by=actor,
            claim_expires_at=expires_at,
            last_heartbeat_at=utc_now_iso(),
        )

    def complete(self, handoff_id: str, *, actor: str, note: Optional[str]) -> HandoffItem:
        return self._transition(
            handoff_id,
            to_status="completed",
            actor=actor,
            action="complete",
            note=note,
            claimed_by=None,
            claim_expires_at=None,
            last_heartbeat_at=None,
        )

    def _release_expired_claims(self, rows: list[HandoffItem]) -> list[HandoffItem]:
        now = datetime.now(timezone.utc)
        changed = False
        updated_rows: list[HandoffItem] = []
        for row in rows:
            if row.status != "claimed" or not row.claim_expires_at:
                updated_rows.append(row)
                continue
            expires = datetime.fromisoformat(row.claim_expires_at.replace("Z", "+00:00"))
            if expires > now:
                updated_rows.append(row)
                continue
            release_time = utc_now_iso()
            events = list(row.events)
            events.append(
                HandoffEvent(
                    at=release_time,
                    by="system",
                    action="release-expired",
                    note=f"claim expired for {row.claimed_by or 'unknown'}",
                )
            )
            updated_rows.append(
                row.model_copy(
                    update={
                        "status": "open",
                        "claimed_by": None,
                        "claim_expires_at": None,
                        "last_heartbeat_at": None,
                        "updated_at": release_time,
                        "events": events,
                    }
                )
            )
            changed = True
        if changed:
            self._store.save_handoffs(updated_rows)
        return updated_rows

    def _transition(
        self,
        handoff_id: str,
        *,
        to_status: str,
        actor: str,
        action: str,
        note: Optional[str],
        claimed_by: Optional[str],
        claim_expires_at: Optional[str] = None,
        last_heartbeat_at: Optional[str] = None,
    ) -> HandoffItem:
        def _run() -> HandoffItem:
            rows = self._release_expired_claims(self._store.load_handoffs())
            idx = next((i for i, row in enumerate(rows) if row.id == handoff_id), None)
            if idx is None:
                raise ValueError(f"handoff not found: {handoff_id}")
            now = utc_now_iso()
            row = rows[idx]
            if action == "claim" and row.status == "claimed" and row.claimed_by != actor:
                raise ValueError(f"handoff already claimed by {row.claimed_by}")
            events = list(row.events)
            events.append(
                HandoffEvent(
                    at=now,
                    by=actor.strip() or "agent",
                    action=action,
                    note=note,
                )
            )
            update_payload = {
                "status": to_status,
                "updated_at": now,
                "events": events,
            }
            if claimed_by is not None or action in {"complete", "release-expired"}:
                update_payload["claimed_by"] = claimed_by
            if claim_expires_at is not None or action == "complete":
                update_payload["claim_expires_at"] = claim_expires_at
            if last_heartbeat_at is not None or action == "complete":
                update_payload["last_heartbeat_at"] = last_heartbeat_at
            updated = row.model_copy(update=update_payload)
            rows[idx] = updated
            self._store.save_handoffs(rows)
            return updated

        return with_state_retry(_run)
