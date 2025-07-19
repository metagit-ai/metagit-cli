#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.yaml_class
"""

from metagit.core.utils import yaml_class


def test_yaml_load():
    yaml_str = "a: 1\nb: [2, 3]"
    loaded = yaml_class.load(yaml_str)
    assert loaded == {"a": 1, "b": [2, 3]}


def test_yaml_load_error():
    result = yaml_class.load(": not yaml :")
    assert isinstance(result, Exception)


def test_yaml_load_empty():
    assert yaml_class.load("") is None
