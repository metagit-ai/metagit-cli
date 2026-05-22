#!/usr/bin/env python
"""
Unit tests for approval queue storage and ApprovalService.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from metagit.core.context.approval_service import ApprovalService


_HEX32 = re.compile(r"^[0-9a-f]{32}$")


def test_request_persists_hex_id_and_pending_status(tmp_path: Path) -> None:
    root = str(tmp_path.resolve())
    svc = ApprovalService(workspace_root=root)
    req = svc.request(
        action="workspace.sync",
        payload={"mode": "pull"},
        requested_by="mcp-agent",
    )
    assert _HEX32.match(req.id)
    assert req.action == "workspace.sync"
    assert req.payload == {"mode": "pull"}
    assert req.requested_by == "mcp-agent"
    assert req.status == "pending"
    assert req.created_at
    assert req.resolved_at is None
    assert req.resolver_note is None

    pending_path = tmp_path / ".metagit" / "approvals" / "pending.json"
    assert pending_path.is_file()
    raw = json.loads(pending_path.read_text(encoding="utf-8"))
    assert raw["requests"][0]["id"] == req.id


def test_list_optional_status_filter(tmp_path: Path) -> None:
    root = str(tmp_path.resolve())
    svc = ApprovalService(workspace_root=root)
    a = svc.request(action="a", payload={}, requested_by="u1")
    b = svc.request(action="b", payload={}, requested_by="u2")
    svc.resolve(request_id=a.id, decision="approved", note="ok")

    all_res = svc.list(status=None)
    assert len(all_res.requests) == 2

    pending_only = svc.list(status="pending")
    assert len(pending_only.requests) == 1
    assert pending_only.requests[0].id == b.id


def test_resolve_sets_status_timestamp_and_note(tmp_path: Path) -> None:
    root = str(tmp_path.resolve())
    svc = ApprovalService(workspace_root=root)
    req = svc.request(action="delete", payload={"path": "x"}, requested_by="human")
    done = svc.resolve(request_id=req.id, decision="denied", note="unsafe")
    assert done.status == "denied"
    assert done.resolved_at
    assert done.resolver_note == "unsafe"


def test_resolve_unknown_id_raises(tmp_path: Path) -> None:
    svc = ApprovalService(workspace_root=str(tmp_path.resolve()))
    with pytest.raises(ValueError, match="not found"):
        svc.resolve(request_id="deadbeef" * 4, decision="approved")


def test_resolve_non_pending_raises(tmp_path: Path) -> None:
    svc = ApprovalService(workspace_root=str(tmp_path.resolve()))
    req = svc.request(action="x", payload={}, requested_by="y")
    svc.resolve(request_id=req.id, decision="approved")
    with pytest.raises(ValueError, match="not pending"):
        svc.resolve(request_id=req.id, decision="denied")


def test_reload_from_disk_shares_queue(tmp_path: Path) -> None:
    root = str(tmp_path.resolve())
    svc_a = ApprovalService(workspace_root=root)
    r = svc_a.request(action="z", payload={"n": 1}, requested_by="agent")
    svc_b = ApprovalService(workspace_root=root)
    listed = svc_b.list()
    assert len(listed.requests) == 1
    assert listed.requests[0].id == r.id
