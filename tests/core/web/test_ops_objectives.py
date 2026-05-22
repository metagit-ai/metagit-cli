#!/usr/bin/env python
"""Minimal coverage for OpsWebHandler objectives endpoints."""

from __future__ import annotations

import json
from pathlib import Path


def test_ops_objectives_get_post_patch(tmp_path: Path) -> None:
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
    cfg_path.write_text(
        "\n".join(
            [
                "workspace:",
                "  path: \".\"",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    ws_root = str(tmp_path.resolve())
    manifest_path = str(manifest.resolve())
    cfg_resolved = str(cfg_path.resolve())

    from metagit.core.web.ops_handler import OpsWebHandler

    handler = OpsWebHandler(
        root=ws_root,
        config_path=manifest_path,
        appconfig_path=cfg_resolved,
        workspace_root=ws_root,
    )
    recorder: list[tuple[int, dict]] = []

    def respond(code: int, body: dict) -> None:
        recorder.append((code, body))

    assert handler.handle("GET", "/v3/ops/objectives", "", b"", respond)
    assert recorder[-1][0] == 200
    assert recorder[-1][1]["objectives"] == []

    create_body = json.dumps(
        {
            "id": "api-a",
            "title": "From HTTP",
            "status": "pending",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    assert handler.handle("POST", "/v3/ops/objectives", "", create_body, respond)
    assert recorder[-1][0] == 200
    saved = recorder[-1][1]
    assert saved["id"] == "api-a"

    patch_body = json.dumps({"status": "done"}, separators=(",", ":")).encode(
        "utf-8",
    )
    assert handler.handle(
        "PATCH",
        "/v3/ops/objectives/api-a",
        "",
        patch_body,
        respond,
    )
    assert recorder[-1][0] == 200
    assert recorder[-1][1]["status"] == "done"
