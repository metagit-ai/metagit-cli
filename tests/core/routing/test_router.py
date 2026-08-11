#!/usr/bin/env python
"""Unit tests for deterministic routing token-overlap scoring."""

from __future__ import annotations

from metagit.core.routing.models import RequestClass
from metagit.core.routing.router import rank_classes, score, tokenize


def test_tokenize_filters_stopwords() -> None:
    tokens = tokenize("Please rotate the expired certificate for me")
    assert "please" not in tokens
    assert "the" not in tokens
    assert "rotate" in tokens
    assert "certificate" in tokens


def test_score_prefers_overlap_on_trigger_tokens() -> None:
    cls = RequestClass(
        id="REQ-CERT",
        title="Rotate cert",
        triggers=["rotate expired certificate", "renew tls cert"],
    )
    confidence, why = score(cls, "please rotate the certificate now")
    assert confidence > 0
    assert why.startswith("matched:")


def test_rank_orders_highest_score_first() -> None:
    classes = [
        RequestClass(
            id="REQ-CERT",
            title="Rotate cert",
            triggers=["rotate expired certificate"],
        ),
        RequestClass(
            id="REQ-WIKI",
            title="Generate wiki",
            triggers=["generate wiki from repository"],
        ),
    ]
    ranked = rank_classes(classes, "rotate certificate", limit=5)
    assert len(ranked) == 1
    assert ranked[0].request_class.id == "REQ-CERT"


def test_rank_tie_breaks_deterministically_by_id() -> None:
    classes = [
        RequestClass(id="REQ-B", title="B", triggers=["sync repo"]),
        RequestClass(id="REQ-A", title="A", triggers=["sync repo"]),
    ]
    ranked = rank_classes(classes, "sync repo", limit=5)
    assert [row.request_class.id for row in ranked] == ["REQ-A", "REQ-B"]


def test_rank_returns_empty_when_no_match() -> None:
    classes = [
        RequestClass(id="REQ-CERT", title="Rotate cert", triggers=["rotate certificate"]),
    ]
    ranked = rank_classes(classes, "design a new logo", limit=5)
    assert ranked == []
