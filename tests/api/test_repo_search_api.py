#!/usr/bin/env python
"""
HTTP API tests for managed repository search.
"""

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from metagit.core.api.server import build_server


def test_repo_search_endpoint_returns_matches(tmp_path: Path) -> None:
    repo_dir = tmp_path / "platform" / "abacus-app"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: abacus-app",
                "          path: platform/abacus-app",
                "          sync: true",
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
        url = f"http://127.0.0.1:{port}/v1/repos/search?q=abacus"
        payload = json.loads(
            urllib.request.urlopen(url, timeout=5).read().decode("utf-8")
        )
        assert payload["matches"][0]["repo_name"] == "abacus-app"
    finally:
        server.shutdown()
        thread.join(timeout=10.0)


def test_repo_resolve_ambiguous_returns_409(tmp_path: Path) -> None:
    app_repo = tmp_path / "platform" / "abacus-app"
    mod_repo = tmp_path / "shared" / "abacus-module"
    app_repo.mkdir(parents=True)
    mod_repo.mkdir(parents=True)
    (app_repo / ".git").mkdir()
    (mod_repo / ".git").mkdir()
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: abacus-app",
                "          path: platform/abacus-app",
                "          sync: true",
                "          tags:",
                "            code: abacus",
                "    - name: shared",
                "      repos:",
                "        - name: abacus-module",
                "          path: shared/abacus-module",
                "          sync: true",
                "          tags:",
                "            code: abacus",
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
        url = f"http://127.0.0.1:{port}/v1/repos/resolve?q=abacus"
        req = urllib.request.Request(url)
        try:
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 409
        else:
            raise AssertionError("expected HTTP 409")
    finally:
        server.shutdown()
        thread.join(timeout=10.0)


def test_unknown_path_returns_404(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
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
        url = f"http://127.0.0.1:{port}/v1/no-such"
        try:
            urllib.request.urlopen(url, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("expected HTTP 404")
    finally:
        server.shutdown()
        thread.join(timeout=10.0)
