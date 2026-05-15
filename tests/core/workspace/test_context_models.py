#!/usr/bin/env python
"""
Unit tests for metagit.core.workspace.context_models
"""

import pytest

from metagit.core.workspace.context_models import (
  ProjectSession,
  validate_env_key,
  validate_env_value,
)


def test_validate_env_key_accepts_metagit_style_keys() -> None:
  assert validate_env_key("METAGIT_PROJECT") == "METAGIT_PROJECT"


def test_validate_env_key_rejects_lowercase() -> None:
  with pytest.raises(ValueError):
    validate_env_key("metagit_project")


def test_validate_env_value_rejects_bearer_token() -> None:
  with pytest.raises(ValueError):
    validate_env_value("Bearer abc123")


def test_project_session_rejects_long_agent_notes() -> None:
  with pytest.raises(ValueError):
    ProjectSession(project_name="alpha", agent_notes="x" * 5000)


def test_project_session_caps_recent_repos() -> None:
  session = ProjectSession(
    project_name="alpha",
    recent_repos=[f"/repo-{idx}" for idx in range(20)],
  )
  assert len(session.recent_repos) == 10
