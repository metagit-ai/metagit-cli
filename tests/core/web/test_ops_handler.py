#!/usr/bin/env python
"""HTTP tests for web ops routes (v3 API)."""

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from metagit.core.web.server import build_web_server


def _start_server(
  tmp_path: Path,
  *,
  manifest_extra: str = "",
) -> tuple[threading.Thread, str]:
  manifest_lines = [
    "name: workspace",
    "kind: application",
    "workspace:",
    "  projects:",
    "    - name: platform",
    "      repos: []",
  ]
  if manifest_extra:
    manifest_lines.extend(manifest_extra.strip().splitlines())
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(manifest_lines) + "\n",
    encoding="utf-8",
  )
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
  base = f"http://127.0.0.1:{port}"
  return thread, base


def _post_json(url: str, payload: dict) -> tuple[int, dict]:
  body = json.dumps(payload).encode("utf-8")
  req = urllib.request.Request(
    url,
    data=body,
    method="POST",
    headers={"Content-Type": "application/json"},
  )
  try:
    with urllib.request.urlopen(req, timeout=10) as resp:
      return resp.status, json.loads(resp.read().decode("utf-8"))
  except urllib.error.HTTPError as exc:
    raw = exc.read().decode("utf-8")
    return exc.code, json.loads(raw) if raw else {}


def test_health_endpoint_returns_ok(tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)
  try:
    status, payload = _post_json(f"{base}/v3/ops/health", {})
    assert status == 200
    assert "ok" in payload
  finally:
    thread.join(timeout=0.1)


def test_prune_preview_empty(tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)
  try:
    status, payload = _post_json(
      f"{base}/v3/ops/prune/preview",
      {"project": "platform"},
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["candidates"] == []
  finally:
    thread.join(timeout=0.1)


def test_sync_dry_run_job_completes(tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)
  try:
    status, created = _post_json(
      f"{base}/v3/ops/sync",
      {"dry_run": True, "repos": ["all"]},
    )
    assert status == 202
    job_id = created["job_id"]
    assert job_id

    deadline = time.time() + 5.0
    final_state = ""
    while time.time() < deadline:
      with urllib.request.urlopen(
        f"{base}/v3/ops/sync/{job_id}",
        timeout=5,
      ) as resp:
        job_status = json.loads(resp.read().decode("utf-8"))
      final_state = job_status["state"]
      if final_state in ("completed", "failed"):
        break
      time.sleep(0.05)

    assert final_state == "completed"
  finally:
    thread.join(timeout=0.1)


def test_open_rejects_unknown_path(tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)
  try:
    status, payload = _post_json(
      f"{base}/v3/ops/open",
      {"path": str(tmp_path / "not-a-managed-repo")},
    )
    assert status == 403
    assert payload["ok"] is False
    assert payload["error"]["kind"] == "forbidden_path"
  finally:
    thread.join(timeout=0.1)


def test_source_sync_manifest_dry_run(monkeypatch, tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)

  def _fake_run_mcp_source_sync(**kwargs):  # noqa: ANN003
    _ = kwargs
    return {"ok": True, "applied": False, "plan": {"discovered_count": 1}}

  monkeypatch.setattr(
    "metagit.core.web.ops_handler.run_mcp_source_sync",
    _fake_run_mcp_source_sync,
  )
  try:
    status, payload = _post_json(
      f"{base}/v3/ops/source-sync",
      {
        "project_name": "platform",
        "from_manifest": True,
        "apply": False,
      },
    )
    assert status == 200
    assert payload["ok"] is True
  finally:
    thread.join(timeout=0.1)


def test_open_managed_repo_uses_echo_editor(tmp_path: Path) -> None:
  sync_root = tmp_path / "sync" / "demo"
  sync_root.mkdir(parents=True)
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: demo",
        "          path: ./demo",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  (tmp_path / "metagit.config.yaml").write_text(
    "\n".join(
      [
        "config:",
        "  editor: echo",
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
  base = f"http://127.0.0.1:{server.server_address[1]}"
  try:
    status, payload = _post_json(
      f"{base}/v3/ops/open",
      {"path": str(sync_root.resolve())},
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["editor"] == "echo"
    assert payload["path"] == str(sync_root.resolve())
  finally:
    server.server_close()
    thread.join(timeout=0.1)


def test_pipeline_providers_endpoint(tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)
  try:
    with urllib.request.urlopen(f"{base}/v3/ops/pipelines/providers", timeout=5) as resp:
      payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert isinstance(payload["providers"], list)
  finally:
    thread.join(timeout=0.1)


def test_pipeline_status_endpoint(tmp_path: Path) -> None:
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: metagit-cli",
        "          url: https://github.com/metagit-ai/metagit-cli.git",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
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
  base = f"http://127.0.0.1:{server.server_address[1]}"
  try:
    with urllib.request.urlopen(f"{base}/v3/ops/pipelines/status", timeout=5) as resp:
      payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert "rows" in payload
    assert isinstance(payload["rows"], list)
  finally:
    server.server_close()
    thread.join(timeout=0.1)
