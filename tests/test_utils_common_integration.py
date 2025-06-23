#!/usr/bin/env python
"""
Integration test for metagit.core.utils.common
"""

from metagit.core.utils import common


def test_common_integration(tmp_path):
    # Create a dict, flatten, merge, and pretty print
    d1 = {"a": {"b": 1}, "c": 2}
    d2 = {"a": {"b": 3}, "d": 4}
    flat1 = common.flatten_dict(d1)
    flat2 = common.flatten_dict(d2)
    merged = common.merge_dicts(d1.copy(), d2)
    pretty_str = common.pretty(merged)
    assert flat1["a.b"] == 1
    assert flat2["a.b"] == 3
    assert merged["a"]["b"] == 3
    assert "a" in pretty_str and "b" in pretty_str and "d" in pretty_str
