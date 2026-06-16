#!/usr/bin/env python

"""Tests for context-aware security steps in prepush-gate."""

import importlib.util
from pathlib import Path


def _prepush_gate_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "prepush-gate.py"
    spec = importlib.util.spec_from_file_location("prepush_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load prepush-gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_security_scan_plan_full_when_unknown() -> None:
    gate = _prepush_gate_module()
    assert gate.security_scan_plan(None) == (True, True, True)
    assert gate.security_scan_plan(set()) == (True, True, True)


def test_security_scan_plan_deps_triggers_sync() -> None:
    gate = _prepush_gate_module()
    assert gate.security_scan_plan({"pyproject.toml"}) == (True, True, True)
    assert gate.security_scan_plan({"uv.lock"}) == (True, True, True)


def test_security_scan_plan_src_without_sync() -> None:
    gate = _prepush_gate_module()
    assert gate.security_scan_plan({"src/metagit/cli/main.py"}) == (
        False,
        True,
        True,
    )


def test_security_scan_plan_skips_docs_only() -> None:
    gate = _prepush_gate_module()
    assert gate.security_scan_plan({"docs/install.md", "README.md"}) == (
        False,
        False,
        False,
    )
    assert gate.security_scan_plan({"web/src/App.tsx"}) == (False, False, False)


def test_pytest_targets_returns_none_when_unknown() -> None:
    gate = _prepush_gate_module()
    assert gate.pytest_targets(None) is None
    assert gate.pytest_targets(set()) is None


def test_pytest_targets_returns_none_for_docs_only() -> None:
    gate = _prepush_gate_module()
    assert gate.pytest_targets({"docs/install.md", "README.md"}) is None


def test_pytest_targets_maps_src_module_to_test_file() -> None:
    gate = _prepush_gate_module()
    targets = gate.pytest_targets({"src/metagit/core/config/models.py"})
    assert targets == ["tests/test_models.py"]


def test_pytest_targets_normalizes_windows_src_paths() -> None:
    gate = _prepush_gate_module()
    targets = gate.pytest_targets({r"src\metagit\core\config\models.py"})
    assert targets == ["tests/test_models.py"]
