#!/usr/bin/env python
"""Redaction helpers for run ledger evidence export."""

from __future__ import annotations

import re
from typing import Any

from metagit.core.routing.models import ControlLoopStep, Run, RunEvidence

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"glpat-[A-Za-z0-9\-_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)


def _scrub_text(value: str) -> str:
    scrubbed = value
    for pattern in _SECRET_PATTERNS:
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    return scrubbed


def _scrub_obj(value: Any) -> Any:
    if isinstance(value, str):
        return _scrub_text(value)
    if isinstance(value, list):
        return [_scrub_obj(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _scrub_obj(item) for key, item in value.items()}
    return value


def redact_evidence(evidence: RunEvidence) -> RunEvidence:
    """Return a copy of evidence with secret-like strings scrubbed."""
    steps = [
        ControlLoopStep(
            name=step.name,
            at=step.at,
            status=step.status,
            detail=_scrub_obj(dict(step.detail)),
        )
        for step in evidence.steps
    ]
    return evidence.model_copy(
        update={
            "digest": _scrub_text(evidence.digest) if evidence.digest else evidence.digest,
            "intent": _scrub_text(evidence.intent) if evidence.intent else evidence.intent,
            "errors": [_scrub_text(item) for item in evidence.errors],
            "steps": steps,
            "redacted": True,
        }
    )


def redact_run(run: Run) -> Run:
    """Return a deep copy of a run with evidence redacted."""
    return run.model_copy(update={"evidence": redact_evidence(run.evidence)}, deep=True)


__all__ = ["redact_evidence", "redact_run"]
