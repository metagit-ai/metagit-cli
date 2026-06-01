#!/usr/bin/env python
"""Tests for YAML string wrapping in config display."""

from metagit.core.config.yaml_display import (
  DEFAULT_WRAP_WIDTH,
  format_yaml_string,
  should_use_literal_block,
  wrap_long_string,
)


def test_wrap_long_string_inserts_newlines_at_word_boundaries() -> None:
  text = "word " * 30
  wrapped = wrap_long_string(text.strip(), wrap_width=40)
  assert "\n" in wrapped
  for line in wrapped.splitlines():
    assert len(line) <= 40


def test_should_use_literal_block_for_long_prose() -> None:
  text = "a" * (DEFAULT_WRAP_WIDTH + 1)
  assert should_use_literal_block(text) is True


def test_format_yaml_string_wraps_long_single_line() -> None:
  text = "Deploy only after " + ("operator approval. " * 8)
  formatted = format_yaml_string(text)
  assert "\n" in formatted
