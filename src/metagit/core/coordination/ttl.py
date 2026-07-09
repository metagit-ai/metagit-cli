#!/usr/bin/env python
"""Shared TTL parsing for ACL leases and handoff claim leases."""

from __future__ import annotations

import re

_TTL_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd])?$")


def parse_ttl_seconds(ttl: str) -> int:
    """Parse duration strings like 300, 30m, 2h, 1d into seconds."""
    normalized = ttl.strip().lower()
    match = _TTL_PATTERN.match(normalized)
    if not match:
        raise ValueError(f"invalid ttl {ttl!r}; use seconds or suffix s/m/h/d")
    value = int(match.group("value"))
    unit = match.group("unit") or "s"
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return value * multiplier


__all__ = ["parse_ttl_seconds"]
