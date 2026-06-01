#!/usr/bin/env python
"""Tests for format payload compaction helpers."""

from __future__ import annotations

from metagit.core.config.models import MetagitConfig
from metagit.core.config.payload_compact import prepare_format_payload, prune_empty_dict_nodes


def test_prune_empty_dict_nodes_removes_empty_maps() -> None:
    pruned = prune_empty_dict_nodes({"observability": {}, "name": "demo"})
    assert pruned == {"name": "demo"}


def test_prepare_format_payload_skips_prune_when_include_defaults() -> None:
    payload = {"observability": {}, "name": "demo"}
    result = prepare_format_payload(payload, MetagitConfig, include_defaults=True)
    assert result == payload
