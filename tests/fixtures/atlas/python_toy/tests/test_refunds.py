#!/usr/bin/env python
"""Tests for toy refund helpers."""

from __future__ import annotations

from toy.refunds import RefundService


def test_issue_idempotent() -> None:
  service = RefundService()
  first = service.issue("order-1", 10.0)
  second = service.issue("order-1", 10.0)
  assert first == second
