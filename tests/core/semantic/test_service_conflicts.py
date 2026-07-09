#!/usr/bin/env python
"""Unit tests for concept conflict hints vs ACL claims."""

from __future__ import annotations

from pathlib import Path

from metagit.core.coordination.claim_service import ClaimService
from metagit.core.semantic.service import SemanticGraphService


def test_conflicts_when_two_agents_claim_same_concept_paths(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  semantic = SemanticGraphService(str(session))
  claims = ClaimService(str(session))
  semantic.declare(
    concept="Authentication",
    repository="demo/api",
    patterns=["backend/auth/**"],
  )
  claims.declare(
    repository="demo/api",
    agent_id="agent-a",
    patterns=["backend/auth/token.py"],
  )
  claims.declare(
    repository="demo/api",
    agent_id="agent-b",
    patterns=["backend/auth/session.py"],
  )

  result = semantic.conflicts(repository="demo/api")

  assert not isinstance(result, Exception)
  assert result.hints
  hint = result.hints[0]
  assert hint.concept_id == "authentication"
  assert set(hint.agent_ids) >= {"agent-a", "agent-b"}


def test_conflicts_empty_when_single_agent_claims_concept_paths(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  semantic = SemanticGraphService(str(session))
  claims = ClaimService(str(session))
  semantic.declare(
    concept="Authentication",
    repository="demo/api",
    patterns=["backend/auth/**"],
  )
  claims.declare(
    repository="demo/api",
    agent_id="agent-a",
    patterns=["backend/auth/token.py"],
  )
  claims.declare(
    repository="demo/api",
    agent_id="agent-a",
    patterns=["backend/auth/session.py"],
  )

  result = semantic.conflicts(repository="demo/api")

  assert not isinstance(result, Exception)
  assert result.hints == []
