# RFC-0010 Semantic Repository Knowledge Graph — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship concept-level ownership storage and query/conflict hints that advise ACL claims without replacing GitNexus or enforcing hard locks.

**Architecture:** New `src/metagit/core/semantic/` package (models, paths, JSON store, `SemanticGraphService`, events). Thin Click CLI `metagit semantic` and MCP tools. Reuse session-root resolution, `JsonListStore` / file-lock patterns, and `patterns_overlap` from ACL claims. Claim check/declare may attach advisory `concept_hints` — never block git.

**Tech Stack:** Python, Pydantic, Click, MCP runtime, existing event feed, pytest. Optional GitNexus read-only import is a deferred phase (not MVP).

**Design:** [2026-07-09-rfc-0010-semantic-kg-design.md](../specs/2026-07-09-rfc-0010-semantic-kg-design.md)  
**Series:** [acl-rfc-series-index](../specs/2026-07-09-acl-rfc-series-index.md)

## Global constraints

- Modality: CLI + MCP + core + docs/skills; no SPA; no `/v3/ops` unless remote-state sharing is required mid-MR.
- Persistence: `.metagit/graph/` under session/manifest root; events at `.metagit/events/semantic.jsonl` (same layout as acl/taskgraph).
- Empty-by-default catalog; `--seed` is opt-in only.
- GitNexus import is Phase 7 (optional) — skip if timeboxed; do not block MVP acceptance.
- Advisory only: never replace Git; never hard-lock concepts.
- ACL branch leases ≠ handoff claim TTL.
- Before editing existing symbols (especially `ClaimService` / `ClaimCheckResult`): GitNexus impact when available; always `task qa:prepush` before hand-off.
- Implement on a feature branch (e.g. `feat/rfc-0010-semantic-kg`), not directly on `main`.

## Out of scope

Hosted KG, replacing GitNexus, hard locks, merge/scheduler/AOS engines, SPA, SQLite/Postgres, required bundled ontology, LLM concept inference.

## File map (create)

| Path | Responsibility |
|------|----------------|
| `src/metagit/core/semantic/__init__.py` | Exports |
| `src/metagit/core/semantic/models.py` | `Concept`, `ConceptOwnership`, conflict/query envelopes, event types |
| `src/metagit/core/semantic/paths.py` | Resolve `.metagit/graph/` + events path |
| `src/metagit/core/semantic/store.py` | Load/save concepts + ownerships with file lock |
| `src/metagit/core/semantic/service.py` | declare/query/owners/conflicts/ingest/seed |
| `src/metagit/core/semantic/events.py` | Append `source=semantic` events |
| `src/metagit/core/semantic/seed.py` | Small optional seed catalog (Authentication, Billing, …) |
| `src/metagit/cli/commands/semantic.py` | Click group |
| `tests/core/semantic/` | Unit tests |
| `tests/cli/commands/test_semantic_cli.py` | CLI tests |
| `tests/core/mcp/test_semantic_tools.py` | MCP tool tests |
| `docs/reference/semantic-ownership.md` | Operator reference |
| `.mex/patterns/semantic-ownership.md` | Recurring runbook |

## File map (modify)

- `src/metagit/cli/main.py` — register `semantic_group`
- `src/metagit/core/coordination/models.py` — optional `concept_hints` on `ClaimCheckResult`
- `src/metagit/core/coordination/claim_service.py` — attach concept hints on check/declare (advisory)
- `src/metagit/core/mcp/runtime.py` + `tool_registry.py` — semantic tools
- `src/metagit/core/context/event_service.py` — merge `source=semantic`
- `scripts/modality-parity.yml` — `semantic_ownership` feature
- `docs/agents.md`, `llms.txt`, `AGENTS.md`, `CHANGELOG.md`, skills cross-links
- `docs/reference/agent-coordination.md` — link to semantic-ownership doc
- `.mex/ROUTER.md`, series index status, `.mex/patterns/INDEX.md`
- `mkdocs.yml` — nav entry for reference doc

---

### Task 1: Models + paths + store

**Files:**
- Create: `src/metagit/core/semantic/__init__.py`
- Create: `src/metagit/core/semantic/models.py`
- Create: `src/metagit/core/semantic/paths.py`
- Create: `src/metagit/core/semantic/store.py`
- Test: `tests/core/semantic/test_semantic_models.py`
- Test: `tests/core/semantic/test_store.py`

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Unit tests for semantic KG models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from metagit.core.semantic.models import Concept, ConceptOwnership


def test_concept_requires_slug_id() -> None:
    with pytest.raises(ValidationError):
        Concept(
            concept_id="Bad Id!",
            name="Bad",
            created_at="2026-07-09T00:00:00+00:00",
            updated_at="2026-07-09T00:00:00+00:00",
        )


def test_ownership_requires_pattern_and_repository() -> None:
    row = ConceptOwnership(
        ownership_id="o1",
        concept_id="authentication",
        repository="demo/api",
        patterns=["**/auth/**"],
        created_at="2026-07-09T00:00:00+00:00",
        updated_at="2026-07-09T00:00:00+00:00",
    )
    assert row.patterns == ["**/auth/**"]
    with pytest.raises(ValidationError):
        ConceptOwnership(
            ownership_id="o2",
            concept_id="authentication",
            repository="demo/api",
            patterns=[],
            created_at="2026-07-09T00:00:00+00:00",
            updated_at="2026-07-09T00:00:00+00:00",
        )
```

```python
#!/usr/bin/env python
"""Unit tests for SemanticGraphStore."""

from __future__ import annotations

from pathlib import Path

from metagit.core.semantic.models import Concept, ConceptOwnership
from metagit.core.semantic.paths import concepts_file, graph_root, ownerships_file
from metagit.core.semantic.store import SemanticGraphStore


def test_store_round_trip(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    store = SemanticGraphStore(str(session))
    concept = Concept(
        concept_id="authentication",
        name="Authentication",
        created_at="2026-07-09T00:00:00+00:00",
        updated_at="2026-07-09T00:00:00+00:00",
    )
    ownership = ConceptOwnership(
        ownership_id="o1",
        concept_id="authentication",
        repository="demo/api",
        patterns=["**/auth/**"],
        created_at="2026-07-09T00:00:00+00:00",
        updated_at="2026-07-09T00:00:00+00:00",
    )
    assert store.save_concepts([concept]) is None
    assert store.save_ownerships([ownership]) is None
    assert graph_root(str(session)).is_dir()
    assert concepts_file(str(session)).is_file()
    assert ownerships_file(str(session)).is_file()
    loaded_c = store.load_concepts()
    loaded_o = store.load_ownerships()
    assert not isinstance(loaded_c, Exception)
    assert not isinstance(loaded_o, Exception)
    assert loaded_c[0].concept_id == "authentication"
    assert loaded_o[0].patterns == ["**/auth/**"]
```

- [ ] **Step 2: Run tests — expect fail**

```bash
uv run pytest tests/core/semantic/test_semantic_models.py tests/core/semantic/test_store.py -q
```

Expected: FAIL (module not found / import error).

- [ ] **Step 3: Implement models, paths, store**

`models.py` essentials:

```python
#!/usr/bin/env python
"""Pydantic models for Semantic Repository Knowledge Graph (RFC-0010)."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

_ID_PATTERN = re.compile(r"^[\w.-]+$")

SemanticEventType = Literal["ConceptDeclared", "ConceptConflictHint", "ConceptIngested"]


def _validate_id(value: str, *, label: str) -> str:
    stripped = value.strip()
    if not stripped or not _ID_PATTERN.match(stripped):
        raise ValueError(f"{label} must match slug pattern [alphanumeric, underscore, dot, hyphen]")
    return stripped


class Concept(BaseModel):
    concept_id: str
    name: str
    description: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str

    @field_validator("concept_id")
    @classmethod
    def validate_concept_id(cls, value: str) -> str:
        return _validate_id(value, label="concept_id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name is required")
        return stripped


class ConceptOwnership(BaseModel):
    ownership_id: str
    concept_id: str
    repository: str  # project/repo
    patterns: list[str] = Field(default_factory=list)
    symbol_hints: list[str] = Field(default_factory=list)
    source: Literal["manual", "ingest", "seed", "gitnexus"] = "manual"
    created_at: str
    updated_at: str

    @field_validator("ownership_id", "concept_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or "/" not in stripped:
            raise ValueError("repository must be project/repo")
        return stripped

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one ownership pattern is required")
        return cleaned


class ConceptConflictHint(BaseModel):
    concept_id: str
    concept_name: str
    repository: str
    overlapping_patterns: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    agent_ids: list[str] = Field(default_factory=list)


class ConceptQueryResult(BaseModel):
    ok: bool = True
    concept: Optional[Concept] = None
    ownerships: list[ConceptOwnership] = Field(default_factory=list)


class ConceptOwnersResult(BaseModel):
    ok: bool = True
    path: str
    repository: str
    concepts: list[Concept] = Field(default_factory=list)
    ownerships: list[ConceptOwnership] = Field(default_factory=list)


class ConceptConflictsResult(BaseModel):
    ok: bool = True
    repository: str
    hints: list[ConceptConflictHint] = Field(default_factory=list)


class SemanticEvent(BaseModel):
    event_id: str
    type: SemanticEventType
    at: str
    payload: dict[str, Any] = Field(default_factory=dict)
```

`paths.py`:

```python
#!/usr/bin/env python
"""Resolve semantic graph persistence paths under the session/manifest root."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.root_resolver import resolve_session_root


def graph_root(session_root: str) -> Path:
    root = resolve_session_root(session_root)
    return Path(root) / ".metagit" / "graph"


def concepts_file(session_root: str) -> Path:
    return graph_root(session_root) / "concepts.json"


def ownerships_file(session_root: str) -> Path:
    return graph_root(session_root) / "ownerships.json"


def events_file(session_root: str) -> Path:
    return Path(resolve_session_root(session_root)) / ".metagit" / "events" / "semantic.jsonl"
```

`store.py`: reuse the lock pattern from `TaskGraphStore` / `JsonListStore` — two documents keyed `concepts` and `ownerships`. Methods: `load_concepts`, `save_concepts`, `load_ownerships`, `save_ownerships`, `update_concepts(mutator)`, `update_ownerships(mutator)`. Returns `T | Exception`.

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/core/semantic/test_semantic_models.py tests/core/semantic/test_store.py -q
```

- [ ] **Step 5: Commit** (when user requests) `feat(semantic): add models and JSON store for RFC-0010`

---

### Task 2: Declare / query / owners in service

**Files:**
- Create: `src/metagit/core/semantic/service.py`
- Test: `tests/core/semantic/test_service_owners.py`

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Unit tests for SemanticGraphService declare/query/owners."""

from __future__ import annotations

from pathlib import Path

from metagit.core.semantic.service import SemanticGraphService


def test_declare_and_owners_round_trip(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    svc = SemanticGraphService(str(session))
    declared = svc.declare(
        concept="Authentication",
        repository="demo/api",
        patterns=["**/auth/**"],
    )
    assert not isinstance(declared, Exception)
    assert declared.concept.concept_id == "authentication"

    owners = svc.owners(path="backend/auth/token.py", repository="demo/api")
    assert not isinstance(owners, Exception)
    assert any(c.concept_id == "authentication" for c in owners.concepts)

    query = svc.query(concept="authentication")
    assert not isinstance(query, Exception)
    assert query.concept is not None
    assert len(query.ownerships) == 1


def test_owners_miss_when_path_outside_pattern(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    svc = SemanticGraphService(str(session))
    svc.declare(concept="Billing", repository="demo/api", patterns=["**/billing/**"])
    owners = svc.owners(path="backend/auth/token.py", repository="demo/api")
    assert not isinstance(owners, Exception)
    assert owners.concepts == []
```

- [ ] **Step 2: Run tests — expect fail**

```bash
uv run pytest tests/core/semantic/test_service_owners.py -q
```

- [ ] **Step 3: Implement `SemanticGraphService`**

Core behavior:

- `declare(concept, repository, patterns, *, symbol_hints=None, source="manual")` — slugify concept name to `concept_id` if needed; upsert concept; append ownership; emit `ConceptDeclared`.
- `query(concept)` — by id or case-insensitive name/alias.
- `owners(path, repository)` — match path against ownership patterns using `patterns_overlap` from `metagit.core.coordination.claim_service` (import the function; do not duplicate).
- All methods return `Result | Exception`.

Slug helper: lowercase, spaces→hyphens, strip non-slug chars; reject empty.

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/core/semantic/test_service_owners.py -q
```

- [ ] **Step 5: Commit** (when user requests) `feat(semantic): declare/query/owners for concept ownership`

---

### Task 3: Conflicts vs active claims

**Files:**
- Modify: `src/metagit/core/semantic/service.py`
- Test: `tests/core/semantic/test_service_conflicts.py`

- [ ] **Step 1: Write failing test**

```python
#!/usr/bin/env python
"""Unit tests for concept conflict hints vs ACL claims."""

from __future__ import annotations

from pathlib import Path

from metagit.core.coordination.claim_service import ClaimService
from metagit.core.semantic.service import SemanticGraphService


def test_conflicts_when_two_agents_claim_same_concept_paths(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    semantic = SemanticGraphService(str(session))
    claims = ClaimService(str(session))
    semantic.declare(
        concept="Authentication",
        repository="demo/api",
        patterns=["backend/auth/**"],
    )
    claims.declare(
        repository="demo/api",
        agent_id="agent-a",
        patterns=["backend/auth/token.py"],
    )
    claims.declare(
        repository="demo/api",
        agent_id="agent-b",
        patterns=["backend/auth/session.py"],
    )
    result = semantic.conflicts(repository="demo/api")
    assert not isinstance(result, Exception)
    assert result.hints
    hint = result.hints[0]
    assert hint.concept_id == "authentication"
    assert set(hint.agent_ids) >= {"agent-a", "agent-b"}
```

- [ ] **Step 2: Implement `conflicts(repository)`**

Logic:

1. Load ownerships for repository.
2. Load active claims via `ClaimService.list(repository=..., status="active")`.
3. For each concept with ≥1 ownership, find active claims whose patterns overlap any ownership pattern (`patterns_overlap`).
4. If ≥2 distinct `agent_id`s touch the same concept (or one claim overlaps ownership while another agent also overlaps), emit `ConceptConflictHint`.
5. Also emit event `ConceptConflictHint` when hints non-empty (optional per call; at least return JSON).
6. Never raise / never mutate claims.

- [ ] **Step 3: Tests pass**

```bash
uv run pytest tests/core/semantic/test_service_conflicts.py -q
```

- [ ] **Step 4: Commit** (when user requests) `feat(semantic): advisory concept conflict hints`

---

### Task 4: Events + WorkspaceEventService merge

**Files:**
- Create: `src/metagit/core/semantic/events.py`
- Modify: `src/metagit/core/context/event_service.py`
- Test: `tests/core/semantic/test_events.py`

- [ ] **Step 1: Write failing test** that declare appends `ConceptDeclared` visible with `source=semantic` via `WorkspaceEventService` (mirror `tests/core/taskgraph/test_events.py` pattern).

- [ ] **Step 2: Implement `SemanticEventStore`** (copy structure from `TaskGraphEventStore`; path `events_file`).

- [ ] **Step 3: Wire into `WorkspaceEventService`** after taskgraph block:

```python
from metagit.core.semantic.events import SemanticEventStore
# ...
semantic_events = SemanticEventStore(self._root).list_events(since=None)
if not isinstance(semantic_events, Exception):
    for event in semantic_events:
        rows.append(
            WorkspaceEvent(
                timestamp=event.at,
                source="semantic",
                kind=event.type,
                id=event.event_id,
                data=dict(event.payload),
            )
        )
```

- [ ] **Step 4: Tests pass;** commit deferred `feat(semantic): emit ConceptDeclared events`

---

### Task 5: Claim check advisory concept hints

**Files:**
- Modify: `src/metagit/core/coordination/models.py` — add optional field
- Modify: `src/metagit/core/coordination/claim_service.py`
- Test: `tests/core/semantic/test_claim_advice.py` (or extend existing claim tests)

**Impact note:** Run GitNexus `impact` on `ClaimService.check` / `ClaimCheckResult` before editing. Additive optional field only — keep default empty list so existing callers stay valid.

- [ ] **Step 1: Extend model**

```python
class ClaimCheckResult(BaseModel):
    ok: bool = True
    conflicts: list[ClaimConflict] = Field(default_factory=list)
    concept_hints: list[dict[str, Any]] = Field(default_factory=list)
```

Prefer importing `ConceptConflictHint` if it avoids circular imports; otherwise `list[dict[str, Any]]` dumped from semantic models is fine for v1.

- [ ] **Step 2: In `ClaimService.check`**, after computing path conflicts, optionally call `SemanticGraphService(session_root).advise_claim_patterns(repository, patterns)` which returns concept hints for overlapping ownerships. Failures from semantic load must not fail claim check (swallow → empty hints).

- [ ] **Step 3: Failing then passing test** — declare concept ownership, `claim check` overlapping pattern → `concept_hints` non-empty; `ok` still True when no path claim conflicts.

- [ ] **Step 4: Commit** (when user requests) `feat(claim): attach advisory concept hints on check`

---

### Task 6: CLI `metagit semantic`

**Files:**
- Create: `src/metagit/cli/commands/semantic.py`
- Modify: `src/metagit/cli/main.py`
- Test: `tests/cli/commands/test_semantic_cli.py`

- [ ] **Step 1: Write failing CLI tests** for `declare` / `query` / `owners` / `conflicts` with `--json` using temp session root (reuse `resolve_acl_roots` / acl_common helpers like claim CLI).

Example invoke pattern (match existing claim CLI tests):

```python
from click.testing import CliRunner
from metagit.cli.main import cli

def test_semantic_declare_owners_json(tmp_path, monkeypatch):
    # write minimal .metagit.yml under tmp_path; chdir or pass --definition
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "semantic", "declare",
            "--definition", str(tmp_path / ".metagit.yml"),
            "--concept", "Authentication",
            "--repository", "demo/api",
            "--pattern", "**/auth/**",
            "--json",
        ],
    )
    assert result.exit_code == 0
```

- [ ] **Step 2: Implement Click group**

Commands:

- `declare --concept --repository --pattern (multiple) [--json]`
- `query --concept [--json]`
- `owners --path --repository [--json]`
- `conflicts --repository [--json]`
- `ingest [--project] [--json]` (stub ok until Task 8; may return empty ingest result)
- `seed [--json]` (Task 8)

Register in `main.py` next to `claim_group`.

- [ ] **Step 3: Tests pass;** commit deferred `feat(cli): add metagit semantic commands`

---

### Task 7: MCP tools + modality parity

**Files:**
- Modify: `src/metagit/core/mcp/tool_registry.py`
- Modify: `src/metagit/core/mcp/runtime.py`
- Modify: `scripts/modality-parity.yml`
- Test: `tests/core/mcp/test_semantic_tools.py`

- [ ] **Step 1: Register ACTIVE-gated tools**

| Tool | Mirrors |
|------|---------|
| `metagit_semantic_declare` | declare |
| `metagit_semantic_query` | query |
| `metagit_semantic_owners` | owners |
| `metagit_semantic_conflicts` | conflicts |
| `metagit_semantic_ingest` | ingest |

Schemas: required strings matching CLI; return `model_dump(mode="json")`.

- [ ] **Step 2: Add modality feature**

```yaml
  - id: semantic_ownership
    description: Concept-level ownership declare/query/owners/conflicts
    service: metagit.core.semantic.service.SemanticGraphService
    reference_doc: docs/reference/semantic-ownership.md
    surfaces:
      cli:
        markers:
          - path: src/metagit/cli/commands/semantic.py
            contains: '@semantic_group.command("declare")'
      mcp:
        markers:
          - path: src/metagit/core/mcp/tool_registry.py
            contains: metagit_semantic_declare
      documentation:
        markers:
          - path: docs/reference/semantic-ownership.md
            contains: "modality:semantic_ownership"
          - path: docs/agents.md
            contains: "modality:semantic_ownership"
      skills:
        markers:
          - path: src/metagit/data/skills/metagit-agent-coordination/SKILL.md
            contains: "modality:semantic_ownership"
          - path: src/metagit/data/skills/metagit-cli/SKILL.md
            contains: "modality:semantic_ownership"
```

- [ ] **Step 3: MCP tests** (mirror `tests/core/mcp/test_task_tools.py` style); commit deferred.

---

### Task 8: Ingest MVP + optional seed

**Files:**
- Create: `src/metagit/core/semantic/seed.py`
- Modify: `service.py` — `ingest`, `seed`
- Test: `tests/core/semantic/test_ingest_seed.py`

- [ ] **Step 1: Seed catalog** — small static list (≤8 concepts), e.g. Authentication (`**/auth/**`, `**/login/**`), Billing (`**/billing/**`, `**/payment/**`), Config (`**/.metagit.yml`, `**/metagit.config.yaml`). `seed()` inserts missing concepts/ownerships with `source="seed"`; idempotent.

- [ ] **Step 2: Ingest MVP** — deterministic only. Preferred cheap source: if workspace index / detect metadata exposes path tags or documentation paths for a repo, map known keywords → concepts. If no reliable signal exists in-repo, implement `ingest` as:

  1. Scan existing ownerships (no-op refresh), and/or
  2. Read optional `.metagit/graph/ingest-hints.json` if present (operator-supplied), and/or
  3. Return `{ok: true, added: 0, skipped: N, reason: "no_ingest_signals"}` without failing.

  Do **not** call GitNexus in this task.

- [ ] **Step 3: Tests** for seed idempotency + ingest no-op / hints file; commit deferred.

---

### Task 9: Optional GitNexus overlay import (deferrable)

**Files:**
- Modify: `service.py` — `ingest(..., source="gitnexus")` behind flag
- CLI: `semantic ingest --gitnexus`
- Test: skip or mock if GitNexus unavailable

- [ ] **Step 1:** Only if Tasks 1–8 green and time remains. Import read-only concept/path hints from GitNexus group/query if a thin adapter already exists; otherwise document as deferred and leave `--gitnexus` returning a clear “not available” JSON error without crashing.

- [ ] **Step 2:** Do not block MVP acceptance on this task.

---

### Task 10: Docs, skills, GROW closeout

**Files:**
- Create: `docs/reference/semantic-ownership.md`
- Create: `.mex/patterns/semantic-ownership.md`
- Modify: `docs/reference/agent-coordination.md`, `docs/agents.md`, `llms.txt`, `AGENTS.md`, skills, `CHANGELOG.md`, `mkdocs.yml`, `.mex/ROUTER.md`, series index, `.mex/patterns/INDEX.md`

- [ ] **Step 1: Write reference doc** covering persistence, CLI/MCP table, advisory claim hints, non-goals (not GitNexus replacement). Include `<!-- modality:semantic_ownership -->`.

- [ ] **Step 2: Update agent-coordination** deferred link: semantic ownership ships in RFC-0010 → link `semantic-ownership.md`.

- [ ] **Step 3: Pattern + INDEX row** for semantic ownership.

- [ ] **Step 4: `task qa:prepush` until green**.

- [ ] **Step 5: `task gitnexus:analyze`**.

- [ ] **Step 6: Commit** (when user requests) `docs: semantic ownership reference and RFC-0010 closeout`.

---

## Acceptance checklist

- [ ] Declare concept + path; `owners` returns it for matching files.
- [ ] Overlapping active claims on same concept produce conflict hint JSON.
- [ ] `claim check` may include `concept_hints` without failing when only concept overlap exists.
- [ ] Does not block git; tests cover overlap logic.
- [ ] Events merge with `source=semantic`.
- [ ] Modality feature `semantic_ownership` registered; reference doc published.
- [ ] Empty-by-default; `--seed` opt-in only.
- [ ] GitNexus import optional / non-blocking.

## Out of scope (do not implement in this MR)

RFC-0011–0013 engines, SPA, SQLite, hard concept locks, replacing GitNexus, required ontology.
