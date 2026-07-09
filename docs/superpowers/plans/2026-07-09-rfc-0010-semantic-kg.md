# RFC-0010 Semantic Repository Knowledge Graph — Implementation Plan

> **For agentic workers:** Expand into bite-sized TDD steps when the RFC-0010 MR starts.

**Goal:** Ship concept-level ownership storage and query/conflict hints that advise ACL claims without replacing GitNexus or enforcing hard locks.

**Architecture:** New `src/metagit/core/semantic/` with concept/ownership models, JSON under `.metagit/graph/`, ingest from manual declare + light detect/index hooks; optional GitNexus import as a later phase inside this RFC if time allows.

**Tech Stack:** Pydantic, Click, MCP, pytest; optional GitNexus CLI/MCP read-only.

**Design:** [2026-07-09-rfc-0010-semantic-kg-design.md](../specs/2026-07-09-rfc-0010-semantic-kg-design.md)

## Out of scope

Hosted KG, replacing GitNexus, hard locks, merge/scheduler engines, SPA, required bundled ontology (empty-by-default; optional seed flag only).

## File map

| Action | Path |
|--------|------|
| Create | `src/metagit/core/semantic/{__init__,models,paths,store,service}.py` |
| Create | `src/metagit/cli/commands/semantic.py` |
| Create | `tests/core/semantic/`, `tests/cli/commands/test_semantic_cli.py` |
| Create | `docs/reference/semantic-ownership.md` |
| Modify | Claim check path (optional warn), MCP, modality-parity, CHANGELOG, ROUTER, series index |

## Phases

- [ ] **Phase 0 — Models/store:** `Concept`, `ConceptOwnership`; `.metagit/graph/` persistence.
- [ ] **Phase 1 — Declare/query/owners:** CLI/MCP; path matching via glob/prefix (reuse claim overlap ideas).
- [ ] **Phase 2 — Conflicts:** Compare active claims / presence vs concept ownership; advisory JSON only.
- [ ] **Phase 3 — Ingest MVP:** Deterministic extract from existing detect/index metadata where cheap; skip if noisy.
- [ ] **Phase 4 — Optional:** `--seed` small catalog; GitNexus overlay import behind flag.
- [ ] **Phase 5 — Docs + parity + QA.**

## Acceptance checklist

- [ ] Declare + owners round-trip.
- [ ] Conflict hint without blocking git.
- [ ] Modality features registered; reference doc published.

## Expand-at-MR-start

Add TDD steps per phase; run GitNexus impact before claim_service integration.
