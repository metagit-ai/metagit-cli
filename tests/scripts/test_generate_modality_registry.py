#!/usr/bin/env python

"""Tests for modality registry markdown generation."""

import importlib.util
from pathlib import Path


def _registry_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "generate_modality_registry.py"
    spec = importlib.util.spec_from_file_location("generate_modality_registry", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load generate_modality_registry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reference_href_rebases_docs_paths_for_registry_location() -> None:
    registry = _registry_module()
    assert registry._reference_href("docs/cli_reference.md") == "../cli_reference.md"
    assert registry._reference_href("docs/agents.md") == "../agents.md"
    assert registry._reference_href("docs/reference/campaigns.md") == "campaigns.md"
