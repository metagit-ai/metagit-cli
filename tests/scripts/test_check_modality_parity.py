#!/usr/bin/env python
"""Smoke test for modality parity registry validation."""

import importlib.util
from pathlib import Path


def _parity_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "check_modality_parity.py"
    spec = importlib.util.spec_from_file_location("check_modality_parity", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load check_modality_parity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_modality_parity_registry_passes() -> None:
    assert _parity_module().main() == 0
