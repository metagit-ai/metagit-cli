#!/usr/bin/env python
"""Search disposable GitHub organization indexes without local checkouts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from metagit.core.detect.fingerprints import matching_paths
from metagit.core.orgindex.store import IndexedRepository, OrgIndexStore, default_index_home, github_index_path
from metagit.core.repo.identity import parse_repository_ref


class OrgSearchHit(BaseModel):
    """One organization-index search match."""

    identity: str
    name: str
    organization: str
    description: Optional[str] = None
    language: Optional[str] = None
    topics: list[str] = Field(default_factory=list)
    detected: list[str] = Field(default_factory=list)
    lifecycle: str = "active"
    presence: str = "indexed"
    url: Optional[str] = None
    pushed_at: Optional[str] = None
    score: int = 0
    match_reasons: list[str] = Field(default_factory=list)


class OrgSearchResult(BaseModel):
    """Organization search envelope."""

    ok: bool = True
    query: Optional[str] = None
    hits: list[OrgSearchHit] = Field(default_factory=list)
    error: Optional[str] = None


class OrgSearchService:
    """Filter indexed repositories by text, language, topic, and fingerprints."""

    def __init__(self, *, index_home: Path | None = None) -> None:
        self._index_home = index_home or default_index_home()

    def search(
        self,
        query: str | None = None,
        *,
        organization: str | None = None,
        language: str | None = None,
        topic: str | None = None,
        has: str | None = None,
        stale_days: int | None = None,
        limit: int = 50,
    ) -> OrgSearchResult:
        stores = self._stores(organization)
        if isinstance(stores, Exception):
            return OrgSearchResult(ok=False, query=query, error=str(stores))
        hits: list[OrgSearchHit] = []
        for store in stores:
            repos = store.list_repositories()
            if isinstance(repos, Exception):
                return OrgSearchResult(ok=False, query=query, error=str(repos))
            for repo in repos:
                hit = self._match(
                    repo,
                    query=query,
                    language=language,
                    topic=topic,
                    has=has,
                    stale_days=stale_days,
                )
                if hit is not None:
                    hits.append(hit)
        hits.sort(key=lambda item: (-item.score, item.name))
        return OrgSearchResult(query=query, hits=hits[: max(limit, 1)])

    def get(self, identifier: str, *, organization: str | None = None) -> IndexedRepository | None | Exception:
        ref = parse_repository_ref(identifier)
        identity = ref.get("identity")
        stores = self._stores(organization or ref.get("organization"))
        if isinstance(stores, Exception):
            return stores
        if identity:
            for store in stores:
                found = store.get(identity)
                if isinstance(found, Exception):
                    return found
                if found is not None:
                    return found
        name = ref.get("name")
        if not name:
            return None
        matches: list[IndexedRepository] = []
        for store in stores:
            found = store.find_by_name(name)
            if isinstance(found, Exception):
                return found
            matches.extend(found)
        if len(matches) == 1:
            return matches[0]
        if not matches:
            return None
        return Exception(f"ambiguous repository '{identifier}'; qualify as org/name")

    def _stores(self, organization: str | None) -> list[OrgIndexStore] | Exception:
        if organization:
            return [OrgIndexStore(github_index_path(organization, home=self._index_home))]
        github_root = self._index_home / "github"
        if not github_root.exists():
            return []
        return [OrgIndexStore(path) for path in sorted(github_root.glob("*.sqlite"))]

    def _match(
        self,
        repo: IndexedRepository,
        *,
        query: str | None,
        language: str | None,
        topic: str | None,
        has: str | None,
        stale_days: int | None,
    ) -> OrgSearchHit | None:
        reasons: list[str] = []
        score = 0
        if language and not _language_matches(repo, language):
            return None
        if language:
            reasons.append(f"language:{language}")
            score += 5
        if topic:
            lowered = topic.lower()
            if lowered not in {item.lower() for item in repo.topics}:
                return None
            reasons.append(f"topic:{topic}")
            score += 5
        if has:
            tag_hit = has.lower() in {item.lower() for item in repo.detected}
            path_hits = matching_paths(repo.fingerprint_paths, has=has)
            if not tag_hit and not path_hits:
                return None
            reasons.append(f"has:{has}")
            score += 8
        if stale_days is not None:
            pushed = _parse_time(repo.pushed_at)
            if pushed is None:
                return None
            cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
            if pushed > cutoff:
                return None
            reasons.append(f"stale_days:{stale_days}")
            score += 3
        if query:
            tokens = [token for token in query.lower().split() if token]
            haystack = " ".join(
                [
                    repo.name.lower(),
                    (repo.description or "").lower(),
                    " ".join(item.lower() for item in repo.topics),
                    " ".join(item.lower() for item in repo.detected),
                    (repo.language or "").lower(),
                ]
            )
            if any(token not in haystack for token in tokens):
                return None
            reasons.append(f"query:{query}")
            score += 4 * len(tokens)
            if repo.name.lower() in {token.lower() for token in tokens}:
                score += 10
        if not reasons and (query or language or topic or has or stale_days is not None):
            return None
        if not reasons:
            reasons.append("indexed")
            score = 1
        return OrgSearchHit(
            identity=repo.identity,
            name=repo.name,
            organization=repo.organization,
            description=repo.description,
            language=repo.language,
            topics=list(repo.topics),
            detected=list(repo.detected),
            lifecycle=repo.lifecycle,
            presence=repo.presence,
            url=repo.html_url or repo.url,
            pushed_at=repo.pushed_at,
            score=score,
            match_reasons=reasons,
        )


def _language_matches(repo: IndexedRepository, language: str) -> bool:
    wanted = _normalize_language(language)
    candidates = [_normalize_language(repo.language or "")]
    candidates.extend(_normalize_language(name) for name in repo.languages)
    return wanted in {item for item in candidates if item}


def _normalize_language(value: str) -> str:
    text = value.strip().lower()
    aliases = {
        "c#": "csharp",
        "csharp": "csharp",
        "cs": "csharp",
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
    }
    return aliases.get(text, text)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
