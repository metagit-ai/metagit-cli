#!/usr/bin/env python
"""HTTP API tests for workspace grep v2 endpoint."""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from metagit.core.api.server import build_server


def _write_grep_fixture(root: Path) -> None:
    (root / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: svc-a",
                "          path: platform/svc-a",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    repo_dir = root / "platform" / "svc-a"
    repo_dir.mkdir(parents=True)
    (repo_dir / "main.py").write_text("def hello():\n    return 'grep-marker'\n", encoding="utf-8")


def test_workspace_grep_requires_query(tmp_path: Path) -> None:
    _write_grep_fixture(tmp_path)
    server = build_server(root=str(tmp_path), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/v2/workspace/grep"
        with urllib.request.urlopen(url, timeout=5) as _response:
            raise AssertionError("expected 400 for missing q")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
        payload = json.loads(exc.read().decode("utf-8"))
        assert payload["ok"] is False
    finally:
        server.shutdown()
        thread.join(timeout=10.0)


def test_workspace_grep_info_returns_ripgrep_status(tmp_path: Path) -> None:
    _write_grep_fixture(tmp_path)
    server = build_server(root=str(tmp_path), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/v2/workspace/grep/info"
        payload = json.loads(urllib.request.urlopen(url, timeout=5).read().decode("utf-8"))
        assert payload["ok"] is True
        data = payload["data"]
        assert "ripgrep_available" in data
        assert "search_backend" in data
        assert data["search_backend"] in {"ripgrep", "python_walk"}
    finally:
        server.shutdown()
        thread.join(timeout=10.0)


def test_workspace_grep_returns_enriched_hits(tmp_path: Path) -> None:
    _write_grep_fixture(tmp_path)
    server = build_server(root=str(tmp_path), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        query = urllib.parse.urlencode({"q": "grep-marker"})
        url = f"http://127.0.0.1:{port}/v2/workspace/grep?{query}"
        payload = json.loads(urllib.request.urlopen(url, timeout=5).read().decode("utf-8"))
        assert payload["ok"] is True
        hits = payload["data"]["hits"]
        assert len(hits) >= 1
        first = hits[0]
        assert first["project_name"] == "platform"
        assert first["repo_name"] == "svc-a"
        assert "grep-marker" in first.get("line", "")
    finally:
        server.shutdown()
        thread.join(timeout=10.0)
