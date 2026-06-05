#!/usr/bin/env python
"""Tests for agent catalog web routes."""

from __future__ import annotations

import json
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread

from metagit.core.web.server import build_web_server


def _start_server(root: Path, appconfig_path: Path) -> tuple[object, str, int]:
    server = build_web_server(
        root=str(root),
        appconfig_path=str(appconfig_path),
        host="127.0.0.1",
        port=0,
    )
    host, port = server.server_address  # type: ignore[assignment]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, host, port


def test_agent_catalog_route(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    appconfig = root / "metagit.config.yaml"
    server, host, port = _start_server(root, appconfig)
    try:
        conn = HTTPConnection(host, port, timeout=10)
        conn.request("GET", "/v3/agents/catalog")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["ok"] is True
        assert len(body["catalog"]["templates"]) >= 10
    finally:
        server.shutdown()  # type: ignore[attr-defined]


def test_agent_overlay_init_route(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    appconfig = root / "metagit.config.yaml"
    server, host, port = _start_server(root, appconfig)
    try:
        conn = HTTPConnection(host, port, timeout=10)
        body = json.dumps({"mode": "minimal", "dry_run": True}).encode("utf-8")
        conn.request(
            "POST",
            "/v3/agents/templates/repo-implementer/overlay/init",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert payload["ok"] is True
        assert payload["overlay"]["dry_run"] is True
    finally:
        server.shutdown()  # type: ignore[attr-defined]


def test_agent_dispatch_plan_route(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    appconfig = root / "metagit.config.yaml"
    server, host, port = _start_server(root, appconfig)
    try:
        conn = HTTPConnection(host, port, timeout=10)
        conn.request(
            "GET",
            "/v3/agents/templates/repo-implementer/dispatch-plan"
            "?vendor=cursor&project=demo&repo=api&task=fix%20tests",
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["ok"] is True
        assert body["plan"]["template_id"] == "repo-implementer"
        assert "launch" in body["plan"]
    finally:
        server.shutdown()  # type: ignore[attr-defined]


def test_agent_preview_route(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    appconfig = root / "metagit.config.yaml"
    server, host, port = _start_server(root, appconfig)
    try:
        conn = HTTPConnection(host, port, timeout=10)
        conn.request(
            "GET",
            "/v3/agents/templates/repo-implementer/preview?vendor=claude_code",
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["ok"] is True
        assert "Repo implementer" in body["preview"]["content"]
    finally:
        server.shutdown()  # type: ignore[attr-defined]
