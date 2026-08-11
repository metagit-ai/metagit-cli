#!/usr/bin/env python
"""Deterministic token-overlap router for request classes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from metagit.core.routing.models import RequestClass

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "please",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
}


@dataclass(frozen=True)
class MatchResult:
    request_class: RequestClass
    confidence: float
    why: str


def tokenize(text: str) -> list[str]:
    """Tokenize free text into lowercase terms with stopword filtering."""
    return [token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS]


def score(request_class: RequestClass, query: str) -> tuple[float, str]:
    """Score a class against query text via best trigger token overlap."""
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0, "empty-query"

    best = 0.0
    why = "no-trigger-match"
    for trigger in request_class.triggers:
        trigger_tokens = set(tokenize(trigger))
        if not trigger_tokens:
            continue
        overlap = query_tokens & trigger_tokens
        if not overlap:
            continue

        # F1-like overlap score keeps ranking stable across short and long triggers.
        value = (2.0 * len(overlap)) / (len(query_tokens) + len(trigger_tokens))
        if value > best:
            best = value
            why = f"matched:{','.join(sorted(overlap))}"

    return round(best, 6), why


def rank_classes(classes: list[RequestClass], query: str, *, limit: int = 5) -> list[MatchResult]:
    """Return highest-confidence class matches for one query."""
    scored: list[MatchResult] = []
    for row in classes:
        confidence, why = score(row, query)
        if confidence > 0:
            scored.append(MatchResult(request_class=row, confidence=confidence, why=why))

    scored.sort(key=lambda item: (-item.confidence, item.request_class.id))
    if limit < 0:
        limit = 0
    return scored[:limit]


__all__ = ["MatchResult", "rank_classes", "score", "tokenize"]
