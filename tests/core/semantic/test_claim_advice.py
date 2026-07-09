#!/usr/bin/env python
"""Unit tests for semantic claim check advisory hints."""

from __future__ import annotations

from pathlib import Path

from metagit.core.coordination.claim_service import ClaimService
from metagit.core.semantic.paths import ownerships_file
from metagit.core.semantic.service import SemanticGraphService


def test_claim_check_includes_concept_hints_without_path_conflicts(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  semantic = SemanticGraphService(str(session))
  declared = semantic.declare(
    concept="Authentication",
    repository="demo/api",
    patterns=["backend/auth/**"],
  )
  assert not isinstance(declared, Exception)

  result = ClaimService(str(session)).check(
    repository="demo/api",
    patterns=["backend/auth/token.py"],
    agent_id="agent-a",
  )

  assert not isinstance(result, Exception)
  assert result.ok is True
  assert result.conflicts == []
  assert result.concept_hints
  assert result.concept_hints[0]["concept_id"] == "authentication"
  assert result.concept_hints[0]["concept_name"] == "Authentication"
  assert result.concept_hints[0]["repository"] == "demo/api"
  assert result.concept_hints[0]["overlapping_patterns"] == ["backend/auth/token.py"]


def test_claim_check_ignores_semantic_store_failures(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  path = ownerships_file(str(session))
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text("{not-json", encoding="utf-8")

  result = ClaimService(str(session)).check(
    repository="demo/api",
    patterns=["backend/auth/token.py"],
    agent_id="agent-a",
  )

  assert not isinstance(result, Exception)
  assert result.ok is True
  assert result.conflicts == []
  assert result.concept_hints == []
