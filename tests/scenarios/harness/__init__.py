#!/usr/bin/env python
"""Test-only multi-agent scenario harness (RFC-0021)."""

__all__ = [
    "AgentPool",
    "ControllableClock",
    "ScenarioDiagnostics",
    "ScenarioWorkspace",
    "SimulatedAgent",
    "assert_scenario",
    "build_document_store",
]


def __getattr__(name: str):
    if name in {"AgentPool", "SimulatedAgent"}:
        from .agents import AgentPool, SimulatedAgent

        return AgentPool if name == "AgentPool" else SimulatedAgent
    if name == "ControllableClock":
        from .clock import ControllableClock

        return ControllableClock
    if name in {"ScenarioDiagnostics", "assert_scenario"}:
        from .diagnostics import ScenarioDiagnostics, assert_scenario

        return ScenarioDiagnostics if name == "ScenarioDiagnostics" else assert_scenario
    if name == "ScenarioWorkspace":
        from .workspace import ScenarioWorkspace

        return ScenarioWorkspace
    if name == "build_document_store":
        from .plane import build_document_store

        return build_document_store
    raise AttributeError(name)
