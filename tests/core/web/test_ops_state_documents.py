#!/usr/bin/env python
"""Coverage for whole-document ops state routes."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.context.models import Objective
from metagit.core.workspace.context_models import utc_now_iso


def _build_handler(tmp_path: Path):
    manifest = Path(tmp_path) / ".metagit.yml"
    manifest.write_text(
        "\n".join(
            [
                "name: web-ops-demo",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: ex",
                "      repos: []",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    cfg_path = tmp_path / "metagit-app.yml"
    cfg_path.write_text("workspace:\n  path: \".\"\n", encoding="utf-8")
    ws_root = str(tmp_path.resolve())

    from metagit.core.web.ops_handler import OpsWebHandler

    handler = OpsWebHandler(
        root=ws_root,
        config_path=str(manifest.resolve()),
        appconfig_path=str(cfg_path.resolve()),
        workspace_root=ws_root,
    )
    recorder: list[tuple[int, dict, dict | None]] = []

    def respond(code: int, body: dict, headers: dict | None = None) -> None:
        recorder.append((code, body, headers))

    return handler, respond, recorder


def test_ops_put_objectives_if_match(tmp_path: Path) -> None:
    handler, respond, recorder = _build_handler(tmp_path)
    assert handler.handle("GET", "/v3/ops/objectives", "", b"", respond)
    etag = recorder[-1][2]["ETag"].strip('"') if recorder[-1][2] else None

    now = utc_now_iso()
    objective = Objective(
        id="doc-a",
        title="Whole doc",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    body = json.dumps({"objectives": [objective.model_dump(mode="json")]}).encode("utf-8")
    headers = {"If-Match": f'"{etag}"'} if etag else {"If-Match": '""'}
    assert handler.handle("PUT", "/v3/ops/objectives", "", body, respond, headers)
    assert recorder[-1][0] == 200
    assert recorder[-1][1]["objectives"][0]["id"] == "doc-a"


def test_ops_handoffs_get_post(tmp_path: Path) -> None:
    handler, respond, recorder = _build_handler(tmp_path)
    assert handler.handle("GET", "/v3/ops/handoffs", "", b"", respond)
    assert recorder[-1][1]["handoffs"] == []

    now = utc_now_iso()
    create_body = json.dumps(
        {
            "id": "handoff-1",
            "title": "Follow up",
            "created_by": "agent",
            "created_at": now,
            "updated_at": now,
        },
    ).encode("utf-8")
    assert handler.handle("POST", "/v3/ops/handoffs", "", create_body, respond)
    assert recorder[-1][0] == 200
    assert recorder[-1][1]["title"] == "Follow up"

    assert handler.handle("GET", "/v3/ops/handoffs", "", b"", respond)
    assert len(recorder[-1][1]["handoffs"]) == 1


def test_ops_events_get(tmp_path: Path) -> None:
    handler, respond, recorder = _build_handler(tmp_path)
    assert handler.handle("GET", "/v3/ops/events", "", b"", respond)
    assert recorder[-1][0] == 200
    assert "events" in recorder[-1][1]


def test_ops_state_routes_use_resolve_backend(tmp_path: Path, monkeypatch) -> None:
    """Whole-doc GET/PUT must honor configured DocumentStore plane (Deployment B)."""
    from unittest.mock import MagicMock

    handler, respond, recorder = _build_handler(tmp_path)
    calls: list[str] = []
    mock_bundle = MagicMock()
    mock_objectives = MagicMock()
    mock_objectives.load.return_value = ([], "tok-obj")
    mock_objectives.save.return_value = "tok-obj-saved"
    mock_approvals = MagicMock()
    mock_approvals.load.return_value = ([], "tok-appr")
    mock_handoffs = MagicMock()
    mock_handoffs.load.return_value = ([], "tok-hand")
    mock_bundle.objectives.return_value = mock_objectives
    mock_bundle.approvals.return_value = mock_approvals
    mock_bundle.handoffs.return_value = mock_handoffs

    def fake_resolve(root: str):
        calls.append(root)
        return mock_bundle

    monkeypatch.setattr("metagit.core.web.ops_handler.resolve_backend", fake_resolve)

    assert handler.handle("GET", "/v3/ops/objectives", "", b"", respond)
    assert handler.handle("GET", "/v3/ops/approvals", "status=all", b"", respond)
    assert handler.handle("GET", "/v3/ops/handoffs", "", b"", respond)
    now = utc_now_iso()
    objective = Objective(
        id="via-resolve",
        title="Plane path",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    body = json.dumps({"objectives": [objective.model_dump(mode="json")]}).encode("utf-8")
    assert handler.handle(
        "PUT",
        "/v3/ops/objectives",
        "",
        body,
        respond,
        {"If-Match": '""'},
    )

    assert calls
    assert all(call == handler._root for call in calls)
    assert mock_objectives.load.called
    assert mock_approvals.load.called
    assert mock_handoffs.load.called
    assert mock_objectives.save.called
    assert recorder[-1][0] == 200
