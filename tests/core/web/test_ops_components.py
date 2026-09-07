#!/usr/bin/env python
"""HTTP tests for GET /v3/ops/components and /v3/ops/components/resolve."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

from metagit.core.web.server import build_web_server

_MANIFEST = """
name: workspace
kind: umbrella
workspace:
  projects:
    - name: platform
      repos:
        - name: core
          path: ./core
          components:
            - name: web
              path: apps/web
              kind: application
              depends_on:
                - api
            - name: api
              path: apps/api
              kind: service
"""


def _start_server(tmp_path: Path):
  (tmp_path / ".metagit.yml").write_text(_MANIFEST.lstrip() + "\n", encoding="utf-8")
  (tmp_path / "metagit.config.yaml").write_text(
    "\n".join(
      [
        "config:",
        "  workspace:",
        "    path: ./sync",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  server = build_web_server(
    root=str(tmp_path),
    appconfig_path=str(tmp_path / "metagit.config.yaml"),
    host="127.0.0.1",
    port=0,
  )
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  port = server.server_address[1]
  return server, thread, f"http://127.0.0.1:{port}"


def _stop_server(server, thread: threading.Thread) -> None:
  server.shutdown()
  server.server_close()
  thread.join(timeout=2)


def _get_json(url: str) -> tuple[int, dict]:
  try:
    with urllib.request.urlopen(url, timeout=10) as resp:
      return resp.status, json.loads(resp.read().decode("utf-8"))
  except urllib.error.HTTPError as exc:
    raw = exc.read().decode("utf-8")
    return exc.code, json.loads(raw) if raw else {}


def test_ops_components_lists_web_id(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    status, payload = _get_json(f"{base}/v3/ops/components")
    assert status == 200
    ids = {row["id"] for row in payload["components"]}
    assert "platform/core/web" in ids
  finally:
    _stop_server(server, thread)


def test_ops_components_resolve_matches_web(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    query = "apps/web/src/x.tsx"
    qs = urlencode({"path": query, "project": "platform", "repo": "core"})
    status, payload = _get_json(f"{base}/v3/ops/components/resolve?{qs}")
    assert status == 200
    assert payload["matched"] is True
    assert payload["path"] == query
    assert payload["name"] == "web"
    assert payload["spec"]["path"] == "apps/web"
  finally:
    _stop_server(server, thread)


def test_ops_components_resolve_missing_path_is_400(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    status, payload = _get_json(f"{base}/v3/ops/components/resolve")
    assert status == 400
    assert payload.get("ok") is False
  finally:
    _stop_server(server, thread)


def test_ops_components_resolve_unmatched_is_200(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    query = "docs/nope.md"
    qs = urlencode({"path": query, "project": "platform", "repo": "core"})
    status, payload = _get_json(f"{base}/v3/ops/components/resolve?{qs}")
    assert status == 200
    assert payload == {"matched": False, "path": query}
  finally:
    _stop_server(server, thread)


def test_ops_components_resolve_invalid_path_is_400(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    qs = urlencode({"path": "../secret", "project": "platform", "repo": "core"})
    status, payload = _get_json(f"{base}/v3/ops/components/resolve?{qs}")
    assert status == 400
    assert payload.get("ok") is False
  finally:
    _stop_server(server, thread)


def test_ops_components_graph_includes_api(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    qs = urlencode({"component": "platform/core/web"})
    status, payload = _get_json(f"{base}/v3/ops/components/graph?{qs}")
    assert status == 200
    neighbor_ids = {row["id"] for row in payload["nodes"]}
    assert "platform/core/api" in neighbor_ids
  finally:
    _stop_server(server, thread)


def test_ops_components_graph_negative_depth_is_400(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    qs = urlencode({"component": "platform/core/web", "depth": "-1"})
    status, payload = _get_json(f"{base}/v3/ops/components/graph?{qs}")
    assert status == 400
    assert payload.get("ok") is False
  finally:
    _stop_server(server, thread)


def test_ops_components_graph_missing_component_is_400(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    status, payload = _get_json(f"{base}/v3/ops/components/graph")
    assert status == 400
    assert payload.get("ok") is False
  finally:
    _stop_server(server, thread)


def _write_detect_workspace(tmp_path: Path) -> None:
  repo = tmp_path / "core"
  (repo / "apps" / "web").mkdir(parents=True)
  (repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: umbrella",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: core",
        "          path: ./core",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  (tmp_path / "metagit.config.yaml").write_text(
    "config:\n  workspace:\n    path: ./sync\n",
    encoding="utf-8",
  )


def _post_json(url: str, payload: dict) -> tuple[int, dict]:
  request = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
  )
  try:
    with urllib.request.urlopen(request, timeout=10) as resp:
      return resp.status, json.loads(resp.read().decode("utf-8"))
  except urllib.error.HTTPError as exc:
    raw = exc.read().decode("utf-8")
    return exc.code, json.loads(raw) if raw else {}


def test_ops_components_detect_lists_web(tmp_path: Path) -> None:
  _write_detect_workspace(tmp_path)
  server = build_web_server(
    root=str(tmp_path),
    appconfig_path=str(tmp_path / "metagit.config.yaml"),
    host="127.0.0.1",
    port=0,
  )
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  port = server.server_address[1]
  try:
    status, payload = _get_json(f"http://127.0.0.1:{port}/v3/ops/components/detect")
    assert status == 200
    names = {row["name"] for row in payload["candidates"]}
    assert "web" in names
  finally:
    _stop_server(server, thread)


def test_ops_components_init_apply_writes_web(tmp_path: Path) -> None:
  _write_detect_workspace(tmp_path)
  server = build_web_server(
    root=str(tmp_path),
    appconfig_path=str(tmp_path / "metagit.config.yaml"),
    host="127.0.0.1",
    port=0,
  )
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  port = server.server_address[1]
  try:
    status, payload = _post_json(
      f"http://127.0.0.1:{port}/v3/ops/components/init",
      {
        "path": "apps/web",
        "project": "platform",
        "repo": "core",
        "kind": "application",
        "apply": True,
      },
    )
    assert status == 200
    assert payload["name"] == "web"
  finally:
    _stop_server(server, thread)


def test_ops_components_graph_unknown_is_404(tmp_path: Path) -> None:
  server, thread, base = _start_server(tmp_path)
  try:
    qs = urlencode({"component": "platform/core/missing"})
    status, payload = _get_json(f"{base}/v3/ops/components/graph?{qs}")
    assert status == 404
    assert payload.get("ok") is False
  finally:
    _stop_server(server, thread)
