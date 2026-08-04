#!/usr/bin/env python
"""Prompt catalog coverage for context-switch kind."""

from __future__ import annotations

from typing import get_args

from metagit.core.prompt.catalog import is_kind_allowed, template_body
from metagit.core.prompt.models import PromptKind


def test_context_switch_kind_is_literal_member() -> None:
  assert "context-switch" in get_args(PromptKind)


def test_context_switch_allowed_for_workspace() -> None:
  assert is_kind_allowed("context-switch", "workspace") is True


def test_context_switch_template_mentions_env_and_objective() -> None:
  body = template_body("context-switch", "workspace")
  assert "METAGIT_PROJECT" in body
  assert "objective" in body.lower()
