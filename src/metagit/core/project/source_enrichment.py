#!/usr/bin/env python
"""
Provider topic and metadata enrichment for source sync discovery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from metagit.core.project.source_models import (
    DiscoveredRepo,
    SourceProvider,
    SourceSpec,
)

if TYPE_CHECKING:
    from metagit.core.providers import ProviderRegistry
    from metagit.core.utils.logging import UnifiedLogger

_ENRICHMENT_WARN_THRESHOLD = 100


def merge_repo_tags(
    existing: dict[str, str],
    incoming: dict[str, str],
    *,
    refresh_metadata: bool,
) -> dict[str, str]:
    """Merge provider tags into existing repo tags without dropping user keys."""
    merged = dict(existing)
    for key, value in incoming.items():
        if key not in merged:
            merged[key] = value
            continue
        if refresh_metadata or not merged[key]:
            merged[key] = value
    return merged


def topics_to_tags(topics: list[str], provider: str) -> dict[str, str]:
    """Convert provider topics to flat repo tag dict."""
    tags = {"source": provider}
    for topic in topics:
        normalized = topic.strip()
        if normalized:
            tags[normalized] = "topic"
    return tags


def enrich_discovered_repos(
    spec: SourceSpec,
    repos: list[DiscoveredRepo],
    registry: ProviderRegistry,
    logger: UnifiedLogger,
) -> list[DiscoveredRepo]:
    """Attach language/topics from provider metadata when configured."""
    if not spec.enrich_topics or not repos:
        return repos

    if len(repos) > _ENRICHMENT_WARN_THRESHOLD and not spec.refresh_metadata:
        logger.warning(f"Skipping per-repo topic enrichment for {len(repos)} repos; use --refresh-metadata to force")
        return repos

    provider = registry.get_provider_by_name(_provider_display_name(spec.provider))
    if provider is None:
        logger.warning(f"No provider registered for {spec.provider.value}")
        return repos

    enriched: list[DiscoveredRepo] = []
    for repo in repos:
        owner, name = _owner_repo_from_full_name(repo.full_name)
        metadata_result = provider.get_repository_metadata(owner, name)
        if isinstance(metadata_result, Exception):
            logger.warning(f"Metadata enrichment failed for {repo.full_name}: {metadata_result}")
            enriched.append(repo)
            continue

        topics = metadata_result.get("topics") or []
        language = metadata_result.get("language")
        enriched.append(
            repo.model_copy(
                update={
                    "topics": list(topics),
                    "language": language,
                }
            )
        )
    return enriched


def _owner_repo_from_full_name(full_name: str) -> tuple[str, str]:
    segments = [segment for segment in full_name.split("/") if segment]
    if len(segments) < 2:
        return full_name, full_name
    return segments[0], segments[-1]


def _provider_display_name(provider: SourceProvider) -> str:
    if provider == SourceProvider.GITHUB:
        return "GitHub"
    return "GitLab"
