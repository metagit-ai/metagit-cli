#!/usr/bin/env python

"""Tests for GitNexus workspace graph ingest helper script."""

import importlib.util
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_INGEST_SCRIPT = (
    _REPO_ROOT / "skills/metagit-gitnexus/scripts/ingest_workspace_graph.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "ingest_workspace_graph",
        _INGEST_SCRIPT,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_tool_calls_from_array(tmp_path: Path) -> None:
    module = _load_module()
    payload = [
        {
            "tool": "gitnexus_cypher",
            "arguments": {"query": "RETURN 1;", "repo": "umbrella"},
        }
    ]
    path = tmp_path / "tool-calls.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = module._load_tool_calls(path)
    assert len(loaded) == 1
    assert loaded[0]["arguments"]["repo"] == "umbrella"
