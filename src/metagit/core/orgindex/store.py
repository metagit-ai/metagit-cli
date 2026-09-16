#!/usr/bin/env python
"""SQLite-backed GitHub organization index (disposable observations)."""

from __future__ import annotations

import gc
import json
import os
import sqlite3
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from metagit.core.repo.identity import github_identity
from metagit.core.repo.models import RepoLifecycle, RepoPresence

SCHEMA_VERSION = 1


class IndexedRepository(BaseModel):
    """One organization-index row."""

    model_config = ConfigDict(extra="forbid")

    identity: str
    provider: str = "github"
    organization: str
    name: str
    full_name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    clone_url: Optional[str] = None
    html_url: Optional[str] = None
    visibility: Optional[str] = None
    lifecycle: RepoLifecycle = "active"
    presence: RepoPresence = "known"
    default_branch: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    pushed_at: Optional[str] = None
    language: Optional[str] = None
    languages: dict[str, int] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    is_fork: bool = False
    is_template: bool = False
    size: Optional[int] = None
    github_id: Optional[str] = None
    open_issues: Optional[int] = None
    open_pulls: Optional[int] = None
    latest_release: Optional[str] = None
    has_codeowners: Optional[bool] = None
    has_readme: Optional[bool] = None
    has_github_actions: Optional[bool] = None
    fingerprint_paths: list[str] = Field(default_factory=list)
    detected: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=lambda: ["github"])
    seen_at: Optional[str] = None
    indexed_at: Optional[str] = None
    pushed_at_indexed: Optional[str] = None


class InferredRelationship(BaseModel):
    """Automatically generated edge stored only in the local index."""

    model_config = ConfigDict(extra="forbid")

    id: str
    from_identity: str
    to_identity: str
    type: str
    provenance: str = "inferred"
    evidence: dict[str, Any] = Field(default_factory=dict)


def default_index_home() -> Path:
    """Return the default index root, honoring ``METAGIT_INDEX_HOME``."""
    override = os.environ.get("METAGIT_INDEX_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".metagit" / "indexes"


def github_index_path(organization: str, *, home: Optional[Path] = None) -> Path:
    """Return the SQLite path for a GitHub organization index."""
    root = home or default_index_home()
    slug = organization.strip().lower().replace("/", "_")
    return root / "github" / f"{slug}.sqlite"


class OrgIndexStore:
    """Load and mutate a disposable GitHub organization SQLite index."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def open(self) -> sqlite3.Connection | Exception:
        """Open (or recreate) the database, recovering from corruption."""
        connection: sqlite3.Connection | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(str(self.path))
            connection.row_factory = sqlite3.Row
            self._ensure_schema(connection)
            return connection
        except sqlite3.DatabaseError as exc:
            _close_sqlite(connection)
            return self._recover(exc)
        except OSError as exc:
            _close_sqlite(connection)
            return Exception(f"Failed to open organization index: {exc}")

    def upsert_repository(self, repo: IndexedRepository) -> IndexedRepository | Exception:
        connection = self.open()
        if isinstance(connection, Exception):
            return connection
        try:
            payload = _row_from_model(repo)
            if tuple(payload.keys()) != _REPOSITORY_COLUMNS:
                return Exception("indexed repository row columns drifted from schema")
            connection.execute(_REPOSITORY_UPSERT_SQL, payload)
            connection.commit()
            return repo
        except sqlite3.Error as exc:
            return Exception(f"Failed to upsert indexed repository: {exc}")
        finally:
            connection.close()

    def get(self, identity: str) -> IndexedRepository | None | Exception:
        connection = self.open()
        if isinstance(connection, Exception):
            return connection
        try:
            row = connection.execute(
                "SELECT * FROM repositories WHERE identity = ?",
                (identity.lower(),),
            ).fetchone()
            return _model_from_row(row) if row is not None else None
        except sqlite3.Error as exc:
            return Exception(f"Failed to read indexed repository: {exc}")
        finally:
            connection.close()

    def find_by_name(self, name: str) -> list[IndexedRepository] | Exception:
        connection = self.open()
        if isinstance(connection, Exception):
            return connection
        try:
            rows = connection.execute(
                "SELECT * FROM repositories WHERE lower(name) = lower(?)",
                (name,),
            ).fetchall()
            return [_model_from_row(row) for row in rows]
        except sqlite3.Error as exc:
            return Exception(f"Failed to search indexed repositories: {exc}")
        finally:
            connection.close()

    def list_repositories(self) -> list[IndexedRepository] | Exception:
        connection = self.open()
        if isinstance(connection, Exception):
            return connection
        try:
            rows = connection.execute("SELECT * FROM repositories ORDER BY name").fetchall()
            return [_model_from_row(row) for row in rows]
        except sqlite3.Error as exc:
            return Exception(f"Failed to list indexed repositories: {exc}")
        finally:
            connection.close()

    def mark_missing(self, seen_identities: set[str], *, seen_at: str) -> int | Exception:
        """Mark previously known repos that vanished from the latest API page as deleted."""
        connection = self.open()
        if isinstance(connection, Exception):
            return connection
        try:
            rows = connection.execute("SELECT identity, lifecycle FROM repositories").fetchall()
            updated = 0
            for row in rows:
                identity = str(row["identity"])
                if identity in seen_identities:
                    continue
                if str(row["lifecycle"]) == "deleted":
                    continue
                connection.execute(
                    "UPDATE repositories SET lifecycle = ?, seen_at = ? WHERE identity = ?",
                    ("deleted", seen_at, identity),
                )
                updated += 1
            connection.commit()
            return updated
        except sqlite3.Error as exc:
            return Exception(f"Failed to mark missing repositories: {exc}")
        finally:
            connection.close()

    def replace_inferred_relationships(
        self,
        relationships: list[InferredRelationship],
    ) -> int | Exception:
        connection = self.open()
        if isinstance(connection, Exception):
            return connection
        try:
            connection.execute("DELETE FROM inferred_relationships")
            for rel in relationships:
                connection.execute(
                    "INSERT INTO inferred_relationships "
                    "(id, from_identity, to_identity, type, provenance, evidence_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        rel.id,
                        rel.from_identity,
                        rel.to_identity,
                        rel.type,
                        rel.provenance,
                        json.dumps(rel.evidence, sort_keys=True),
                    ),
                )
            connection.commit()
            return len(relationships)
        except sqlite3.Error as exc:
            return Exception(f"Failed to store inferred relationships: {exc}")
        finally:
            connection.close()

    def list_inferred_relationships(self) -> list[InferredRelationship] | Exception:
        connection = self.open()
        if isinstance(connection, Exception):
            return connection
        try:
            rows = connection.execute("SELECT * FROM inferred_relationships").fetchall()
            return [
                InferredRelationship(
                    id=str(row["id"]),
                    from_identity=str(row["from_identity"]),
                    to_identity=str(row["to_identity"]),
                    type=str(row["type"]),
                    provenance=str(row["provenance"] or "inferred"),
                    evidence=json.loads(row["evidence_json"] or "{}"),
                )
                for row in rows
            ]
        except sqlite3.Error as exc:
            return Exception(f"Failed to list inferred relationships: {exc}")
        finally:
            connection.close()

    def set_meta(self, key: str, value: str) -> None | Exception:
        connection = self.open()
        if isinstance(connection, Exception):
            return connection
        try:
            connection.execute(
                "INSERT INTO index_meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            connection.commit()
            return None
        except sqlite3.Error as exc:
            return Exception(f"Failed to write index metadata: {exc}")
        finally:
            connection.close()

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS repositories (
              identity TEXT PRIMARY KEY,
              provider TEXT NOT NULL,
              organization TEXT NOT NULL,
              name TEXT NOT NULL,
              full_name TEXT,
              description TEXT,
              url TEXT,
              clone_url TEXT,
              html_url TEXT,
              visibility TEXT,
              lifecycle TEXT NOT NULL DEFAULT 'active',
              presence TEXT NOT NULL DEFAULT 'known',
              default_branch TEXT,
              created_at TEXT,
              updated_at TEXT,
              pushed_at TEXT,
              language TEXT,
              languages_json TEXT,
              topics_json TEXT,
              is_fork INTEGER NOT NULL DEFAULT 0,
              is_template INTEGER NOT NULL DEFAULT 0,
              size INTEGER,
              github_id TEXT,
              open_issues INTEGER,
              open_pulls INTEGER,
              latest_release TEXT,
              has_codeowners INTEGER,
              has_readme INTEGER,
              has_github_actions INTEGER,
              fingerprints_json TEXT,
              detected_json TEXT,
              provenance_json TEXT,
              seen_at TEXT,
              indexed_at TEXT,
              pushed_at_indexed TEXT
            );
            CREATE TABLE IF NOT EXISTS inferred_relationships (
              id TEXT PRIMARY KEY,
              from_identity TEXT NOT NULL,
              to_identity TEXT NOT NULL,
              type TEXT NOT NULL,
              provenance TEXT NOT NULL DEFAULT 'inferred',
              evidence_json TEXT
            );
            CREATE TABLE IF NOT EXISTS index_meta (
              key TEXT PRIMARY KEY,
              value TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories(name);
            CREATE INDEX IF NOT EXISTS idx_repositories_language ON repositories(language);
            """
        )
        connection.execute(
            "INSERT INTO index_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        connection.commit()

    def _recover(self, exc: sqlite3.DatabaseError) -> sqlite3.Connection | Exception:
        try:
            if self.path.exists():
                _quarantine_corrupt_index(self.path)
            connection = sqlite3.connect(str(self.path))
            connection.row_factory = sqlite3.Row
            self._ensure_schema(connection)
            return connection
        except Exception as recover_exc:
            return Exception(f"Organization index is corrupt ({exc}); recovery failed: {recover_exc}")


def _close_sqlite(connection: sqlite3.Connection | None) -> None:
    """Close a SQLite connection, ignoring close errors."""
    if connection is None:
        return
    with suppress(sqlite3.Error):
        connection.close()
    gc.collect()


def _quarantine_corrupt_index(path: Path) -> None:
    """Move a corrupt index aside. Windows may still hold a lock after a failed open."""
    backup = path.with_suffix(path.suffix + ".corrupt")
    try:
        path.replace(backup)
        return
    except OSError:
        pass
    backup.write_bytes(path.read_bytes())
    try:
        path.unlink()
        return
    except OSError:
        pass
    path.write_bytes(b"")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def indexed_from_github_payload(organization: str, payload: dict[str, Any]) -> IndexedRepository:
    """Map a GitHub repository list payload onto an index row."""
    name = str(payload.get("name") or "").strip()
    identity = github_identity(organization, name)
    visibility = payload.get("visibility")
    if not visibility:
        visibility = "private" if payload.get("private") else "public"
    archived = bool(payload.get("archived"))
    lifecycle: RepoLifecycle = "archived" if archived else "active"
    topics = [str(item) for item in (payload.get("topics") or [])]
    return IndexedRepository(
        identity=identity,
        organization=organization.lower(),
        name=name,
        full_name=payload.get("full_name"),
        description=payload.get("description"),
        url=payload.get("html_url") or payload.get("clone_url"),
        clone_url=payload.get("clone_url"),
        html_url=payload.get("html_url"),
        visibility=str(visibility),
        lifecycle=lifecycle,
        presence="indexed",
        default_branch=payload.get("default_branch"),
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
        pushed_at=payload.get("pushed_at"),
        language=payload.get("language"),
        topics=topics,
        is_fork=bool(payload.get("fork")),
        is_template=bool(payload.get("is_template")),
        size=payload.get("size"),
        github_id=str(payload.get("id")) if payload.get("id") is not None else None,
        open_issues=payload.get("open_issues_count"),
        provenance=["github"],
        seen_at=utc_now(),
        indexed_at=utc_now(),
    )


def _row_from_model(repo: IndexedRepository) -> dict[str, Any]:
    return {
        "identity": repo.identity,
        "provider": repo.provider,
        "organization": repo.organization,
        "name": repo.name,
        "full_name": repo.full_name,
        "description": repo.description,
        "url": repo.url,
        "clone_url": repo.clone_url,
        "html_url": repo.html_url,
        "visibility": repo.visibility,
        "lifecycle": repo.lifecycle,
        "presence": repo.presence,
        "default_branch": repo.default_branch,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at,
        "pushed_at": repo.pushed_at,
        "language": repo.language,
        "languages_json": json.dumps(repo.languages, sort_keys=True),
        "topics_json": json.dumps(repo.topics, sort_keys=True),
        "is_fork": int(repo.is_fork),
        "is_template": int(repo.is_template),
        "size": repo.size,
        "github_id": repo.github_id,
        "open_issues": repo.open_issues,
        "open_pulls": repo.open_pulls,
        "latest_release": repo.latest_release,
        "has_codeowners": None if repo.has_codeowners is None else int(repo.has_codeowners),
        "has_readme": None if repo.has_readme is None else int(repo.has_readme),
        "has_github_actions": None if repo.has_github_actions is None else int(repo.has_github_actions),
        "fingerprints_json": json.dumps(repo.fingerprint_paths, sort_keys=True),
        "detected_json": json.dumps(repo.detected, sort_keys=True),
        "provenance_json": json.dumps(repo.provenance, sort_keys=True),
        "seen_at": repo.seen_at,
        "indexed_at": repo.indexed_at,
        "pushed_at_indexed": repo.pushed_at_indexed,
    }


_REPOSITORY_COLUMNS: tuple[str, ...] = (
    "identity",
    "provider",
    "organization",
    "name",
    "full_name",
    "description",
    "url",
    "clone_url",
    "html_url",
    "visibility",
    "lifecycle",
    "presence",
    "default_branch",
    "created_at",
    "updated_at",
    "pushed_at",
    "language",
    "languages_json",
    "topics_json",
    "is_fork",
    "is_template",
    "size",
    "github_id",
    "open_issues",
    "open_pulls",
    "latest_release",
    "has_codeowners",
    "has_readme",
    "has_github_actions",
    "fingerprints_json",
    "detected_json",
    "provenance_json",
    "seen_at",
    "indexed_at",
    "pushed_at_indexed",
)
_REPOSITORY_UPSERT_SQL = (
    "INSERT INTO repositories (identity, provider, organization, name, full_name, "
    "description, url, clone_url, html_url, visibility, lifecycle, presence, "
    "default_branch, created_at, updated_at, pushed_at, language, languages_json, "
    "topics_json, is_fork, is_template, size, github_id, open_issues, open_pulls, "
    "latest_release, has_codeowners, has_readme, has_github_actions, fingerprints_json, "
    "detected_json, provenance_json, seen_at, indexed_at, pushed_at_indexed) "
    "VALUES (:identity, :provider, :organization, :name, :full_name, :description, "
    ":url, :clone_url, :html_url, :visibility, :lifecycle, :presence, :default_branch, "
    ":created_at, :updated_at, :pushed_at, :language, :languages_json, :topics_json, "
    ":is_fork, :is_template, :size, :github_id, :open_issues, :open_pulls, "
    ":latest_release, :has_codeowners, :has_readme, :has_github_actions, "
    ":fingerprints_json, :detected_json, :provenance_json, :seen_at, :indexed_at, "
    ":pushed_at_indexed) ON CONFLICT(identity) DO UPDATE SET "
    "provider=excluded.provider, organization=excluded.organization, name=excluded.name, "
    "full_name=excluded.full_name, description=excluded.description, url=excluded.url, "
    "clone_url=excluded.clone_url, html_url=excluded.html_url, "
    "visibility=excluded.visibility, lifecycle=excluded.lifecycle, "
    "presence=excluded.presence, default_branch=excluded.default_branch, "
    "created_at=excluded.created_at, updated_at=excluded.updated_at, "
    "pushed_at=excluded.pushed_at, language=excluded.language, "
    "languages_json=excluded.languages_json, topics_json=excluded.topics_json, "
    "is_fork=excluded.is_fork, is_template=excluded.is_template, size=excluded.size, "
    "github_id=excluded.github_id, open_issues=excluded.open_issues, "
    "open_pulls=excluded.open_pulls, latest_release=excluded.latest_release, "
    "has_codeowners=excluded.has_codeowners, has_readme=excluded.has_readme, "
    "has_github_actions=excluded.has_github_actions, "
    "fingerprints_json=excluded.fingerprints_json, detected_json=excluded.detected_json, "
    "provenance_json=excluded.provenance_json, seen_at=excluded.seen_at, "
    "indexed_at=excluded.indexed_at, pushed_at_indexed=excluded.pushed_at_indexed"
)


def _model_from_row(row: sqlite3.Row) -> IndexedRepository:
    def _json_list(value: Any) -> list[str]:
        if not value:
            return []
        loaded = json.loads(value)
        return [str(item) for item in loaded] if isinstance(loaded, list) else []

    def _json_dict(value: Any) -> dict[str, int]:
        if not value:
            return {}
        loaded = json.loads(value)
        if not isinstance(loaded, dict):
            return {}
        return {str(key): int(val) for key, val in loaded.items()}

    def _bool(value: Any) -> Optional[bool]:
        if value is None:
            return None
        return bool(value)

    return IndexedRepository(
        identity=str(row["identity"]),
        provider=str(row["provider"]),
        organization=str(row["organization"]),
        name=str(row["name"]),
        full_name=row["full_name"],
        description=row["description"],
        url=row["url"],
        clone_url=row["clone_url"],
        html_url=row["html_url"],
        visibility=row["visibility"],
        lifecycle=row["lifecycle"],
        presence=row["presence"],
        default_branch=row["default_branch"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        pushed_at=row["pushed_at"],
        language=row["language"],
        languages=_json_dict(row["languages_json"]),
        topics=_json_list(row["topics_json"]),
        is_fork=bool(row["is_fork"]),
        is_template=bool(row["is_template"]),
        size=row["size"],
        github_id=row["github_id"],
        open_issues=row["open_issues"],
        open_pulls=row["open_pulls"],
        latest_release=row["latest_release"],
        has_codeowners=_bool(row["has_codeowners"]),
        has_readme=_bool(row["has_readme"]),
        has_github_actions=_bool(row["has_github_actions"]),
        fingerprint_paths=_json_list(row["fingerprints_json"]),
        detected=_json_list(row["detected_json"]),
        provenance=_json_list(row["provenance_json"]) or ["github"],
        seen_at=row["seen_at"],
        indexed_at=row["indexed_at"],
        pushed_at_indexed=row["pushed_at_indexed"],
    )
