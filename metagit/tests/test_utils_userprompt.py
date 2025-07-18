#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.userprompt
"""

from metagit.core.utils import userprompt


def test_yes_no_prompt_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert userprompt.yes_no_prompt("Continue?") is True


def test_yes_no_prompt_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert userprompt.yes_no_prompt("Continue?") is False


def test_yes_no_prompt_invalid(monkeypatch):
    responses = iter(["maybe", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    assert userprompt.yes_no_prompt("Continue?") is True
