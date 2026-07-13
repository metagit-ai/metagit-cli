#!/usr/bin/env python
"""Collector protocols for AOS subsystem aggregation."""

from __future__ import annotations

from typing import Protocol

from metagit.core.aos.models import AosSubsystemSection


class SubsystemCollector(Protocol):
    """Collect per-subsystem status sections for an AOS snapshot."""

    def collect_all(self) -> dict[str, AosSubsystemSection]:
        """Return subsystem key → section (always includes expected keys)."""
        ...


__all__ = ["SubsystemCollector"]
