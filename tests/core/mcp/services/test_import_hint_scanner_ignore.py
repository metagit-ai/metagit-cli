#!/usr/bin/env python
"""Import hint scanner must not walk node_modules / gitignored trees."""

from __future__ import annotations

from pathlib import Path

from metagit.core.mcp.services.import_hint_scanner import ImportHintScanner


def test_terraform_scan_skips_node_modules(tmp_path: Path) -> None:
    root = tmp_path / "infra"
    other = tmp_path / "modules"
    other.mkdir()
    (other / ".git").mkdir()
    (root / "live").mkdir(parents=True)
    (root / "live" / "main.tf").write_text(
        f'source = "{other.as_posix()}"\n',
        encoding="utf-8",
    )
    (root / "node_modules" / "x").mkdir(parents=True)
    (root / "node_modules" / "x" / "junk.tf").write_text(
        'source = "/should/not/matter"\n',
        encoding="utf-8",
    )
    path_map = {str(other.resolve()): "repo:alpha/modules"}
    scanner = ImportHintScanner()
    hints = scanner.scan_repo(str(root), path_map)
    evidence = " ".join(e for h in hints for e in h.get("evidence", []))
    assert "node_modules" not in evidence
    assert scanner.last_walk_stats is not None
    assert scanner.last_walk_stats.dirs_pruned >= 1
