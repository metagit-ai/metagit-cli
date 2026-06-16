#!/usr/bin/env python
"""Tests for web logo generation script."""

import importlib.util
from pathlib import Path


def _logo_script():
    path = Path(__file__).resolve().parents[2] / "scripts" / "generate_web_logo.py"
    spec = importlib.util.spec_from_file_location("generate_web_logo", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load generate_web_logo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_web_logo_is_idempotent() -> None:
    module = _logo_script()
    assert module.generate() == 0
    assert module.PNG_OUT.is_file()
