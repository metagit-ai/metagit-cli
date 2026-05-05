#!/usr/bin/env python
"""
Upstream issue hint ranking service.
"""

from typing import Any


class UpstreamHintService:
    """Rank repositories likely to contain upstream root causes."""

    _category_terms: dict[str, list[str]] = {
        "terraform": ["terraform", "module", "variable", ".tf", "provider"],
        "docker": ["docker", "dockerfile", "image", "from", "container"],
        "infra": ["infra", "network", "cluster", "vpc", "subnet"],
        "ci": ["workflow", "pipeline", "actions", "runner", "build"],
    }

    def rank(
        self,
        blocker: str,
        repo_context: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return ranked repository candidates for the blocker description."""
        blocker_lower = blocker.lower()
        results: list[dict[str, Any]] = []

        for repo in repo_context:
            score = self._score_repo(blocker_lower=blocker_lower, repo=repo)
            results.append(
                {
                    "repo_name": repo.get("repo_name"),
                    "repo_path": repo.get("repo_path"),
                    "score": score,
                    "rationale": self._rationale(
                        blocker_lower=blocker_lower, repo=repo
                    ),
                }
            )

        return sorted(results, key=lambda row: row["score"], reverse=True)

    def _score_repo(self, blocker_lower: str, repo: dict[str, Any]) -> float:
        score = 0.0
        name = str(repo.get("repo_name", "")).lower()
        project = str(repo.get("project_name", "")).lower()
        path = str(repo.get("repo_path", "")).lower()

        for terms in self._category_terms.values():
            if any(term in blocker_lower for term in terms):
                for term in terms:
                    if term in name:
                        score += 2.0
                    if term in project:
                        score += 1.0
                    if term in path:
                        score += 1.0

        if repo.get("sync") is True:
            score += 0.2
        if repo.get("exists") is True:
            score += 0.1
        return score

    def _rationale(self, blocker_lower: str, repo: dict[str, Any]) -> str:
        name = str(repo.get("repo_name", "unknown"))
        if "terraform" in blocker_lower:
            return f"{name} aligns with terraform-related blocker terms."
        if "docker" in blocker_lower:
            return f"{name} aligns with docker-related blocker terms."
        return f"{name} is ranked by metadata overlap with blocker text."
