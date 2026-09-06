#!/usr/bin/env python
"""Tests for Component pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from metagit.core.component.models import Component, ComponentCommand, ComponentRef
from metagit.core.workspace.agent_profile_models import AgentProfile


def test_minimal_component_requires_name_and_path() -> None:
  component = Component(name="web", path="apps/web")
  assert component.name == "web"
  assert component.path == "apps/web"
  assert component.kind is None
  assert component.depends_on == []
  assert component.commands == {}
  assert component.tags == {}


def test_missing_name_or_path_fails() -> None:
  with pytest.raises(ValidationError):
    Component(path="apps/web")  # type: ignore[call-arg]
  with pytest.raises(ValidationError):
    Component(name="web")  # type: ignore[call-arg]


def test_git_only_fields_are_forbidden() -> None:
  with pytest.raises(ValidationError):
    Component(name="web", path="apps/web", url="https://example.com/web.git")  # type: ignore[call-arg]


def test_full_declarative_component() -> None:
  component = Component(
    name="web",
    path="apps/web",
    description="Frontend",
    kind="application",
    language="typescript",
    language_version=22,
    package_manager="pnpm",
    frameworks=["react", "vite"],
    commands={
      "lint": "pnpm --filter web lint",
      "test": ComponentCommand(command="pnpm --filter web test"),
    },
    depends_on=["api", ComponentRef(project="acme", repo="platform", component="auth")],
    produces=["web-container"],
    deploys_to=["production-web"],
    skills=["typescript", "react"],
    tags={"layer": "frontend"},
    agent_instructions="Prefer the web AGENTS.md",
    agent_profile=AgentProfile(skills=["metagit-cli"]),
  )
  assert component.language_version == "22"
  assert component.commands["lint"] == "pnpm --filter web lint"
  assert isinstance(component.commands["test"], ComponentCommand)
  assert component.depends_on[0] == "api"
  assert component.depends_on[1].component == "auth"  # type: ignore[union-attr]


def test_empty_command_string_fails() -> None:
  with pytest.raises(ValidationError):
    Component(name="web", path="apps/web", commands={"lint": "  "})


def test_empty_command_object_fails() -> None:
  with pytest.raises(ValidationError):
    ComponentCommand(command=" ")


def test_agent_prompt_alias() -> None:
  component = Component(name="web", path="apps/web", agent_prompt="hello")  # type: ignore[call-arg]
  assert component.agent_instructions == "hello"


def test_component_ref_requires_component() -> None:
  with pytest.raises(ValidationError):
    ComponentRef(project="acme", repo="platform")  # type: ignore[call-arg]
