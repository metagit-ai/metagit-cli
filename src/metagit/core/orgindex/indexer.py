#!/usr/bin/env python
"""Index a GitHub organization into the local SQLite observation store."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from metagit.core.appconfig.models import AppConfig
from metagit.core.detect.fingerprints import tags_for_paths
from metagit.core.orgindex.github_client import (
    GitHubOrgApi,
    RequestsGitHubOrgClient,
    resolve_github_api_base,
    resolve_github_token,
)
from metagit.core.orgindex.store import (
    IndexedRepository,
    InferredRelationship,
    OrgIndexStore,
    github_index_path,
    indexed_from_github_payload,
    utc_now,
)


class OrgIndexResult(BaseModel):
    """Summary of an organization index run."""

    ok: bool = True
    organization: str
    provider: str = "github"
    index_path: str
    indexed: int = 0
    updated: int = 0
    discovered: int = 0
    removed: int = 0
    inferred_relationships: int = 0
    mode: str = "incremental"
    error: Optional[str] = None


class GitHubOrgIndexer:
    """Enumerate GitHub org repositories without cloning them."""

    def __init__(
        self,
        *,
        app_config: AppConfig | None = None,
        client: GitHubOrgApi | None = None,
        index_home: Path | None = None,
    ) -> None:
        self._app_config = app_config
        self._client = client
        self._index_home = index_home

    def index(
        self,
        organization: str,
        *,
        refresh: bool = False,
        full: bool = False,
    ) -> OrgIndexResult:
        org = organization.strip()
        if not org:
            return OrgIndexResult(ok=False, organization="", index_path="", error="organization is required")
        path = github_index_path(org, home=self._index_home)
        result = OrgIndexResult(
            organization=org.lower(),
            index_path=str(path),
            mode="full" if full else ("refresh" if refresh else "incremental"),
        )
        client = self._client or self._build_client()
        if isinstance(client, Exception):
            result.ok = False
            result.error = str(client)
            return result

        payloads = client.list_org_repos(org)
        if isinstance(payloads, Exception):
            result.ok = False
            result.error = str(payloads)
            return result

        store = OrgIndexStore(path)
        existing = store.list_repositories()
        if isinstance(existing, Exception):
            result.ok = False
            result.error = str(existing)
            return result
        existing_by_id = {item.identity: item for item in existing}
        seen: set[str] = set()
        now = utc_now()

        for payload in payloads:
            name = str(payload.get("name") or "").strip()
            if not name:
                continue
            row = indexed_from_github_payload(org, payload)
            previous = existing_by_id.get(row.identity)
            if previous is not None:
                row.fingerprint_paths = list(previous.fingerprint_paths)
                row.detected = list(previous.detected)
                row.languages = dict(previous.languages)
                row.open_pulls = previous.open_pulls
                row.latest_release = previous.latest_release
                row.has_codeowners = previous.has_codeowners
                row.has_readme = previous.has_readme
                row.has_github_actions = previous.has_github_actions
                row.pushed_at_indexed = previous.pushed_at_indexed
                row.provenance = sorted(set(previous.provenance + ["github"]))
            enrich = full or previous is None or (
                refresh and (previous.pushed_at != row.pushed_at or not previous.fingerprint_paths)
            )
            if enrich:
                self._enrich(client, row, previous=previous, full=full)
            written = store.upsert_repository(row)
            if isinstance(written, Exception):
                result.ok = False
                result.error = str(written)
                return result
            seen.add(row.identity)
            result.indexed += 1
            if previous is None:
                result.discovered += 1
            else:
                result.updated += 1

        missing = store.mark_missing(seen, seen_at=now)
        if isinstance(missing, Exception):
            result.ok = False
            result.error = str(missing)
            return result
        result.removed = missing

        inferred = _infer_topic_relationships(store)
        if isinstance(inferred, Exception):
            result.ok = False
            result.error = str(inferred)
            return result
        result.inferred_relationships = inferred
        store.set_meta("organization", org.lower())
        store.set_meta("updated_at", now)
        return result

    def _build_client(self) -> RequestsGitHubOrgClient | Exception:
        token = resolve_github_token(self._app_config)
        if not token:
            return Exception("GitHub API token is not configured")
        if self._app_config is not None and not self._app_config.providers.github.enabled:
            return Exception("GitHub provider is disabled in app config")
        return RequestsGitHubOrgClient(
            token=token,
            base_url=resolve_github_api_base(self._app_config),
        )

    def _enrich(
        self,
        client: GitHubOrgApi,
        row: IndexedRepository,
        *,
        previous: IndexedRepository | None,
        full: bool,
    ) -> None:
        owner = row.organization
        name = row.name
        if full or not row.languages:
            languages = client.get_languages(owner, name)
            if not isinstance(languages, Exception):
                row.languages = languages
        if full or previous is None or previous.pushed_at != row.pushed_at or not row.fingerprint_paths:
            ref = row.default_branch or "HEAD"
            paths = client.get_tree_paths(owner, name, ref)
            if not isinstance(paths, Exception):
                row.fingerprint_paths = paths
                row.detected = tags_for_paths(paths)
                lowered = {path.lower() for path in paths}
                row.has_readme = any(path.rsplit("/", 1)[-1].startswith("readme") for path in lowered)
                row.has_codeowners = any(path.endswith("codeowners") for path in lowered)
                row.has_github_actions = any(path.startswith(".github/workflows/") for path in lowered)
                row.pushed_at_indexed = row.pushed_at
        if full:
            pulls = client.get_open_pull_count(owner, name)
            if not isinstance(pulls, Exception):
                row.open_pulls = pulls
            release = client.get_latest_release(owner, name)
            if not isinstance(release, Exception):
                row.latest_release = release
        row.presence = "indexed"
        row.indexed_at = utc_now()


def _infer_topic_relationships(store: OrgIndexStore) -> int | Exception:
    repos = store.list_repositories()
    if isinstance(repos, Exception):
        return repos
    active = [item for item in repos if item.lifecycle == "active"]
    relationships: list[InferredRelationship] = []
    for index, left in enumerate(active):
        left_topics = {topic.lower() for topic in left.topics if topic}
        if len(left_topics) < 3:
            continue
        for right in active[index + 1 :]:
            right_topics = {topic.lower() for topic in right.topics if topic}
            shared = sorted(left_topics & right_topics)
            if len(shared) < 3:
                continue
            if left.language and right.language and left.language != right.language:
                continue
            rel_id = f"similar:{left.identity}:{right.identity}"
            relationships.append(
                InferredRelationship(
                    id=rel_id,
                    from_identity=left.identity,
                    to_identity=right.identity,
                    type="similar_to",
                    provenance="inferred",
                    evidence={"shared_topics": shared},
                )
            )
    written = store.replace_inferred_relationships(relationships)
    if isinstance(written, Exception):
        return written
    return written
