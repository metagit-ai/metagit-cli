#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.fuzzyfinder
"""

from metagit.core.utils import fuzzyfinder
from metagit.core.utils.fuzzyfinder import FuzzyFinderApp, FuzzyFinderConfig


def test_fuzzyfinder_basic():
    collection = ["apple", "banana", "grape", "apricot"]
    results = list(fuzzyfinder.fuzzyfinder("ap", collection))
    assert "apple" in results
    assert "apricot" in results
    assert "banana" not in results


def test_fuzzyfinder_empty():
    assert list(fuzzyfinder.fuzzyfinder("", ["a", "b"])) == ["a", "b"]
    assert list(fuzzyfinder.fuzzyfinder("x", [])) == []


def test_fuzzyfinder_no_match():
    collection = ["cat", "dog"]
    assert list(fuzzyfinder.fuzzyfinder("zebra", collection)) == []


def test_fuzzyfinder_app_search_not_capped_by_max_results():
    config = FuzzyFinderConfig(items=["a", "b", "c"], max_results=1)
    app = FuzzyFinderApp(config)
    results = app._search("")
    assert results == ["a", "b", "c"]
