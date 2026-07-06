#!/usr/bin/env python
"""Tests for handoff lease and heartbeat behavior."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from metagit.core.context.handoff_service import HandoffService, parse_ttl_seconds
from metagit.core.workspace.context_models import utc_now_iso


def test_parse_ttl_seconds() -> None:
    assert parse_ttl_seconds("30") == 30
    assert parse_ttl_seconds("30m") == 1800
    assert parse_ttl_seconds("2h") == 7200


def test_expired_claim_releases_on_list(tmp_path: Path) -> None:
    store_path = tmp_path / ".metagit" / "sessions" / "handoffs.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    now = utc_now_iso()
    payload = {
        "handoffs": [
            {
                "id": "abc123",
                "title": "work",
                "status": "claimed",
                "created_by": "agent",
                "claimed_by": "worker",
                "claim_expires_at": expired,
                "last_heartbeat_at": now,
                "payload": {},
                "created_at": now,
                "updated_at": now,
                "events": [],
            }
        ],
    }
    store_path.write_text(json.dumps(payload), encoding="utf-8")
    service = HandoffService(workspace_root=str(tmp_path))
    rows = service.list().handoffs
    assert rows[0].status == "open"
    assert rows[0].claimed_by is None
