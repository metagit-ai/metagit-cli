#!/usr/bin/env python
"""Refund helpers for the python-toy Atlas fixture."""

from __future__ import annotations


class RefundService:
  """Issue refunds for toy orders."""

  def issue(self, order_id: str, amount: float) -> str:
    """Return a deterministic refund identifier."""
    return f"refund-{order_id}-{amount}"
