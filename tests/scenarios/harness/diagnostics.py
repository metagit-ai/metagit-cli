#!/usr/bin/env python
"""Failure diagnostics for multi-agent scenarios."""

from __future__ import annotations

from typing import Any

import pytest

from .workspace import ScenarioWorkspace


class ScenarioDiagnostics:
    """Accumulate agent timeline entries and dump on assertion failure."""

    def __init__(self, workspace: ScenarioWorkspace) -> None:
        self.workspace = workspace
        self.timeline: list[dict[str, Any]] = []

    def record(
        self,
        *,
        agent_id: str,
        action: str,
        outcome: str,
        error: str | None = None,
        at: str | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "at": at or "n/a",
            "agent_id": agent_id,
            "action": action,
            "outcome": outcome,
        }
        if error:
            entry["error"] = error
        self.timeline.append(entry)

    def dump(self) -> dict[str, Any]:
        snap = self.workspace.snapshot()
        return {
            "timeline": list(self.timeline),
            "workspace_snapshot": snap,
            "suggested_commands": [
                "metagit aos doctor --json",
                "metagit lease list --json",
                "metagit claim list --json",
                "metagit worktree gc",
            ],
            "artifact_paths": snap.get("artifact_paths", []),
        }


def assert_scenario(
    condition: bool,
    diagnostics: ScenarioDiagnostics,
    *,
    message: str,
    record_property: Any | None = None,
) -> None:
    """Assert with structured diagnostics attached for pytest failure output."""
    if condition:
        return
    payload = diagnostics.dump()
    if record_property is not None:
        record_property("scenario_diagnostics", payload)
    pytest.fail(f"{message}\n\nscenario_diagnostics={payload!r}")
