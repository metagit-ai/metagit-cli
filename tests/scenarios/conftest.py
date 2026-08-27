#!/usr/bin/env python
"""Scenario pytest hooks and markers (RFC-0021)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCENARIOS_ROOT = Path(__file__).resolve().parent
if str(_SCENARIOS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCENARIOS_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "nightly: heavier scenario variants for nightly CI")
    config.addinivalue_line("markers", "scenario_http: DocumentStore HTTP stub variants")
    config.addinivalue_line("markers", "requires_harness: needs RFC-0017 harness run envelope")
    config.addinivalue_line(
        "markers",
        "subprocess_isolation: crash isolation via subprocess kill",
    )
    config.addinivalue_line("markers", "slow: scenarios that may exceed typical unit budgets")


@pytest.fixture
def scenario_workspace(tmp_path):
    """Bootstrap a default scenario workspace with two ready task nodes."""
    from tests.scenarios.harness.workspace import ScenarioWorkspace

    return ScenarioWorkspace.bootstrap(tmp_path)
