#!/usr/bin/env python
"""
Tests for source sync topic enrichment helpers.
"""

from metagit.core.project.source_enrichment import merge_repo_tags, topics_to_tags


def test_merge_tags_preserves_user_keys() -> None:
    existing = {"owner": "platform", "custom": "keep"}
    incoming = {"source": "github", "python": "topic", "custom": "topic"}
    merged = merge_repo_tags(existing, incoming, refresh_metadata=False)
    assert merged["custom"] == "keep"
    assert merged["python"] == "topic"
    assert merged["source"] == "github"


def test_refresh_metadata_overwrites_topic_values() -> None:
    existing = {"python": "old"}
    incoming = {"python": "topic"}
    merged = merge_repo_tags(existing, incoming, refresh_metadata=True)
    assert merged["python"] == "topic"


def test_topics_to_tags_includes_source() -> None:
    tags = topics_to_tags(["python", "api"], "github")
    assert tags["source"] == "github"
    assert tags["python"] == "topic"
