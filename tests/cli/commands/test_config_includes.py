#!/usr/bin/env python
"""CLI coverage for split-manifest validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_config_validate_json_reports_broken_fragment(tmp_path: Path) -> None:
    fragment = tmp_path / ".metagit.d" / "projects"
    fragment.mkdir(parents=True)
    (fragment / "alpha.yml").write_text(
        "workspace:\n  projects:\n    - name: alpha\n      unexpected: true\n      repos: []\n",
        encoding="utf-8",
    )
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: umbrella\nkind: umbrella\nincludes:\n  - .metagit.d/projects/alpha.yml\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "metagit.cli.main", "config", "validate", "-c", str(manifest), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    sources = payload["sources"]
    assert any(item["role"] == "root" and item["path"].endswith(".metagit.yml") for item in sources)
    assert any("alpha.yml" in item["path"] and item["role"] == "fragment" for item in sources)
    assert payload["errors"]
    joined = json.dumps(payload["errors"])
    assert "alpha.yml" in joined
    assert "unexpected" in joined or "Extra" in joined
