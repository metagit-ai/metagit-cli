#!/usr/bin/env python
"""HTTP API tests for workspace catalog v2 endpoints."""

import json
import threading
import urllib.request
from pathlib import Path

from metagit.core.api.server import build_server


def test_catalog_project_and_repo_crud(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects: []",
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
        base = f"http://127.0.0.1:{port}"

        projects = json.loads(
            urllib.request.urlopen(f"{base}/v2/projects", timeout=5).read().decode(
                "utf-8"
            )
        )
        assert projects["data"]["project_count"] == 0

        add_body = json.dumps({"name": "platform"}).encode("utf-8")
        add_req = urllib.request.Request(
            f"{base}/v2/projects",
            data=add_body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        added = json.loads(urllib.request.urlopen(add_req, timeout=5).read().decode("utf-8"))
        assert added["ok"] is True

        repo_body = json.dumps(
            {
                "project": "platform",
                "name": "svc-a",
                "path": "platform/svc-a",
                "sync": True,
            }
        ).encode("utf-8")
        repo_req = urllib.request.Request(
            f"{base}/v2/repos",
            data=repo_body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        repo_added = json.loads(
            urllib.request.urlopen(repo_req, timeout=5).read().decode("utf-8")
        )
        assert repo_added["ok"] is True

        repos = json.loads(
            urllib.request.urlopen(
                f"{base}/v2/repos?project=platform", timeout=5
            ).read().decode("utf-8")
        )
        assert repos["data"]["repo_count"] == 1

        delete_repo = urllib.request.Request(
            f"{base}/v2/repos/platform/svc-a",
            method="DELETE",
        )
        urllib.request.urlopen(delete_repo, timeout=5).read()

        delete_project = urllib.request.Request(
            f"{base}/v2/projects/platform",
            method="DELETE",
        )
        urllib.request.urlopen(delete_project, timeout=5).read()
    finally:
        server.shutdown()
        thread.join(timeout=10.0)
