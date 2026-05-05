#!/usr/bin/env python
"""
Deterministic discovery context packaging for config bootstrap.
"""

from pathlib import Path


class DiscoveryContextService:
    """Create deterministic discovery payloads for sampling prompts."""

    def build_context(self, repo_root: str) -> dict[str, str]:
        """Build a minimal deterministic context from repository files."""
        root = Path(repo_root).expanduser().resolve()
        hints: list[str] = []
        for candidate in ["pyproject.toml", "Dockerfile", ".github/workflows"]:
            path = root / candidate
            if path.exists():
                hints.append(candidate)

        return {
            "repo_root": str(root),
            "detected_artifacts": ", ".join(hints) if hints else "none",
            "instruction": "Generate valid .metagit.yml YAML only.",
        }
