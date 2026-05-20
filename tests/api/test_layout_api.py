#!/usr/bin/env python
"""HTTP API tests for workspace layout v2 endpoints."""

import json
import threading
import urllib.request
from pathlib import Path

from metagit.core.api.server import build_server


def test_layout_project_rename_api(tmp_path: Path) -> None:
    sync_root = tmp_path / "sync"
    sync_root.mkdir()
    (sync_root / "alpha").mkdir()
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    server = build_server(root=str(tmp_path), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        body = json.dumps({"to_name": "apps"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v2/projects/alpha/rename",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        payload = json.loads(urllib.request.urlopen(req, timeout=5).read().decode("utf-8"))
        assert payload["ok"] is True
    finally:
        server.shutdown()
        thread.join(timeout=10.0)
