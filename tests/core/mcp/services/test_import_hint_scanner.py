#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.import_hint_scanner
"""

import json
from pathlib import Path

from metagit.core.mcp.services.import_hint_scanner import ImportHintScanner


def test_scan_package_json_file_dependency(tmp_path: Path) -> None:
    lib = tmp_path / "lib-repo"
    app = tmp_path / "app-repo"
    lib.mkdir()
    app.mkdir()
    (app / "package.json").write_text(
        json.dumps({"dependencies": {"lib": "file:../lib-repo"}}),
        encoding="utf-8",
    )
    path_to_id = {
        str(lib.resolve()): "repo:shared/lib-repo",
        str(app.resolve()): "repo:apps/app-repo",
    }
    scanner = ImportHintScanner()

    hints = scanner.scan_repo(repo_path=str(app), path_to_repo_id=path_to_id)

    assert hints
    assert hints[0]["to_id"] == "repo:shared/lib-repo"
