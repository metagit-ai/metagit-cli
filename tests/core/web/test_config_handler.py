#!/usr/bin/env python
"""HTTP tests for web config tree routes (v3 API)."""

import json
import threading
import urllib.request
from pathlib import Path

from metagit.core.web.server import build_web_server


def _start_server(
  tmp_path: Path,
  *,
  appconfig_name: str = "metagit.config.yaml",
) -> tuple[threading.Thread, str]:
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  (tmp_path / appconfig_name).write_text(
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
    appconfig_path=str(tmp_path / appconfig_name),
    host="127.0.0.1",
    port=0,
  )
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  port = server.server_address[1]
  base = f"http://127.0.0.1:{port}"
  return thread, base


def test_get_metagit_config_tree(tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)
  try:
    payload = json.loads(
      urllib.request.urlopen(
        f"{base}/v3/config/metagit/tree",
        timeout=5,
      ).read().decode("utf-8")
    )
    assert payload["ok"] is True
    assert payload["target"] == "metagit"
    assert payload["saved"] is False
    name_node = next(
      child for child in payload["tree"]["children"] if child["key"] == "name"
    )
    assert name_node["value"] == "workspace"
  finally:
    thread.join(timeout=0.1)


def test_patch_metagit_set_name_without_save(tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)
  try:
    patch_body = json.dumps(
      {
        "save": False,
        "operations": [{"op": "set", "path": "name", "value": "renamed"}],
      }
    ).encode("utf-8")
    patch_req = urllib.request.Request(
      f"{base}/v3/config/metagit",
      data=patch_body,
      method="PATCH",
      headers={"Content-Type": "application/json"},
    )
    patched = json.loads(
      urllib.request.urlopen(patch_req, timeout=5).read().decode("utf-8")
    )
    assert patched["saved"] is False
    name_node = next(
      child for child in patched["tree"]["children"] if child["key"] == "name"
    )
    assert name_node["value"] == "renamed"

    on_disk = (tmp_path / ".metagit.yml").read_text(encoding="utf-8")
    assert "name: workspace" in on_disk
  finally:
    thread.join(timeout=0.1)


def test_patch_metagit_set_name_with_save(tmp_path: Path) -> None:
  thread, base = _start_server(tmp_path)
  try:
    patch_body = json.dumps(
      {
        "save": True,
        "operations": [{"op": "set", "path": "name", "value": "saved-name"}],
      }
    ).encode("utf-8")
    patch_req = urllib.request.Request(
      f"{base}/v3/config/metagit",
      data=patch_body,
      method="PATCH",
      headers={"Content-Type": "application/json"},
    )
    patched = json.loads(
      urllib.request.urlopen(patch_req, timeout=5).read().decode("utf-8")
    )
    assert patched["saved"] is True
    name_node = next(
      child for child in patched["tree"]["children"] if child["key"] == "name"
    )
    assert name_node["value"] == "saved-name"

    on_disk = (tmp_path / ".metagit.yml").read_text(encoding="utf-8")
    assert "name: saved-name" in on_disk
  finally:
    thread.join(timeout=0.1)
