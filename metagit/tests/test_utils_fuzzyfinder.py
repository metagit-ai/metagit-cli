#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.fuzzyfinder
"""

from metagit.core.utils import fuzzyfinder


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
