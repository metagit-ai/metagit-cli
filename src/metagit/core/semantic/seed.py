#!/usr/bin/env python
"""Static semantic concept seed catalog for RFC-0010."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SemanticSeedCatalogItem(BaseModel):
    """A small deterministic seed concept and its ownership patterns."""

    concept: str
    patterns: list[str] = Field(min_length=1)


SEED_CATALOG: tuple[SemanticSeedCatalogItem, ...] = (
    SemanticSeedCatalogItem(
        concept="Authentication",
        patterns=["**/auth/**", "**/login/**"],
    ),
    SemanticSeedCatalogItem(
        concept="Billing",
        patterns=["**/billing/**", "**/payment/**"],
    ),
    SemanticSeedCatalogItem(
        concept="Config",
        patterns=["**/.metagit.yml", "**/metagit.config.yaml", "**/config/**"],
    ),
    SemanticSeedCatalogItem(
        concept="CI/CD",
        patterns=["**/.github/workflows/**", "**/.gitlab-ci.yml", "**/Taskfile.yml"],
    ),
    SemanticSeedCatalogItem(
        concept="Documentation",
        patterns=["**/docs/**", "**/README.md", "**/llms.txt"],
    ),
    SemanticSeedCatalogItem(
        concept="Testing",
        patterns=["**/tests/**", "**/test/**"],
    ),
    SemanticSeedCatalogItem(
        concept="Deployment",
        patterns=["**/deploy/**", "**/Dockerfile", "**/docker-compose*.yml"],
    ),
)


__all__ = ["SEED_CATALOG", "SemanticSeedCatalogItem"]
