# Agent Reliability Series Index (RFC-0019+)

**Status:** Living index  
**Date:** 2026-08-27  
**Audience:** Coding agents working on [metagit-cli](https://github.com/metagit-ai/metagit-cli)  
**Scope:** Evolve the existing Agent Operating System surface (ACL / AOS RFCs 0007–0014 + routing run foundations) without redesign.  
**Related series:**
- [ACL RFC series 0007–0013](2026-07-09-acl-rfc-series-index.md) + [Atlas 0014](2026-07-14-rfc-0014-atlas-design.md)
- [Central State Plane series 0015–0018](2026-07-31-central-state-plane-series-index.md)

## Why this series exists

AOS already composes scheduling, ACL, task graph, merge, and context compile. Agents still lack durable actionable evidence of what they did, safe crash recovery, multi-agent scenario coverage, clearer discovery/onboarding, and declarative mutation policy. This series ships those reliability and adoption upgrades as small, reviewable PRs — preferably report-only / dry-run first.

## Numbering lock (do not reuse 0016–0018)

RFC numbers **0016–0018 are reserved** by the central-state-plane series:

| RFC | Title (plane series) | Status |
|-----|----------------------|--------|
| 0015 | Central State Plane | Implemented |
| 0016 | Org Catalog Backend | Proposed |
| 0017 | Agentic Workload Harness | Proposed |
| 0018 | Pluggable Ontology Layer | Proposed |

An earlier draft roadmap that numbered “Run Ledger” as RFC-0016 is **superseded**. Run-evidence work folds into **existing routing + RFC-0017**; new agent-reliability RFCs start at **0019**.

### Collision remapping (authoritative)

| Draft title (2026-08-27) | Authoritative home |
|--------------------------|--------------------|
| Run Ledger & Agent Action Evidence | Extend shipped `metagit.core.routing` + finish [RFC-0017 harness](2026-07-31-rfc-0017-agentic-workload-harness-design.md) (`harness.runs`, heartbeat, `aos next` wiring) |
| Failure Recovery & Control-Loop Resilience | **RFC-0019** (this series) |
| Discovery & Onboarding Surfaces | **RFC-0020** |
| Multi-Agent Scenario Test Harness | **RFC-0021** |
| Policy Engine for Mutating Classes | **RFC-0022** |
| Workspace Federation & Org-Scale Identity | **RFC-0023** (coordinate with plane RFC-0016) |
| Plugin / Detector / Skill Extension Points | **RFC-0024** |
| Workspace Index & Grep Scaling | **RFC-0025** |
| Agent OS Quickstart narrative | **Docs PR series** (no RFC) |

## Existing foundations to reuse

- **Routing run ledger (shipped):** `Run` / `RunEvidence` in `metagit.core.routing`; CLI `metagit run open|close|list`; default storage under `knowledge/requests/runs` via `RoutingConfig.runs`.
- **AOS (RFC-0013):** `metagit aos|coord status|doctor|next`; doctor exists; recover / rich recipes do not.
- **Plane (RFC-0015):** DocumentStore backends; reserved `harness.*` namespaces for RFC-0017.

## Dependency graph

```text
Routing run ledger (shipped) ──┐
RFC-0013 AOS ──────────────────┼─► RFC-0017 Harness (plane series; run evidence + envelopes)
RFC-0015 DocumentStore ────────┘         │
                                         ├─► RFC-0019 Failure recovery / aos recover
                                         └─► RFC-0022 Policy (audit into run ledger)
Docs quickstart (no RFC) ──► unblocks adoption for all below
RFC-0020 Discovery / health
RFC-0021 Multi-agent scenario harness
RFC-0023 Federation (deps plane 0016)
RFC-0024 Plugins
RFC-0025 Workspace index
```

## Status table

| ID | Title | Priority | Effort | Design | Plan | Status |
|----|-------|----------|--------|--------|------|--------|
| (docs) | Agent OS Quickstart + control-loop narrative | P1 | S | — | — | **Shipped** ([agents-quickstart.md](../../agents-quickstart.md), [examples/agent-aos-loop/](../../../examples/agent-aos-loop/)) |
| 0017 | Agentic Workload Harness + run-evidence completion | P0 | M | [design](2026-07-31-rfc-0017-agentic-workload-harness-design.md) · [completion](2026-08-27-rfc-0017-run-evidence-completion-design.md) | in-tree | **Shipped MVP** on `feat/agent-reliability-series` |
| 0019 | Failure Recovery & Control-Loop Resilience | P0 | M | [design](2026-08-27-rfc-0019-failure-recovery-design.md) | in-tree | **Shipped MVP** (recover/heartbeat + recipes) |
| 0020 | Discovery & Onboarding Surfaces | P1 | S–M | [design](2026-08-27-rfc-0020-discovery-onboarding-design.md) | in-tree | **Shipped MVP** (`workspace health|summary`) |
| 0021 | Multi-Agent Scenario Test Harness | P1 | M–L | [design](2026-08-27-rfc-0021-multi-agent-scenarios-design.md) | in-tree | **Shipped MVP** (`tests/scenarios/`) |
| 0022 | Policy Engine for Mutating Classes | P2 | M | [design](2026-08-27-rfc-0022-policy-engine-design.md) | in-tree | **Shipped MVP** (`policy eval` report-only; enforce at mutation points follow-up) |
| — | Secrets & Redaction Hardening | P2 | S | [design](2026-08-27-secrets-redaction-hardening-design.md) | pending | Proposed |
| 0023 | Workspace Federation & Org-Scale Identity | P2 | L | [design](2026-08-27-rfc-0023-federation-design.md) | pending | Proposed |
| 0024 | Plugin / Detector / Skill Extension Points | P2 | M–L | [design](2026-08-27-rfc-0024-plugins-design.md) | pending | Proposed |
| 0025 | Workspace Index & Grep Scaling | P3 | M | [design](2026-08-27-rfc-0025-workspace-index-design.md) | pending | Proposed |

## Work package summaries

### Docs (no RFC): Agent OS Quickstart

**Problem:** Rich surface is spread across many docs; new agents struggle to find the canonical control loop.

**Work:**
- Add `docs/agents-quickstart.md` (or expand `docs/agents.md`) with a day-1 control-loop diagram + commands.
- Point `llms.txt`, `AGENTS.md`, and `metagit prompt workspace --kind session-start` at it.
- Minimal example under `examples/agent-aos-loop/`.
- Ensure skill `metagit-aos` surfaces the quickstart.

**Acceptance:** A new agent can go install → context pack → `aos next` → work → complete in &lt; 10 minutes of reading.

### RFC-0017 completion: Run evidence (plane series)

**Problem:** Agents lack durable, queryable evidence of what they did, why, and what failed.

**Proposed (build on shipped routing + 0017 design):**
- Formalize evidence capture: intent → route class → ACL bind → context compile → task nodes → mutations → outcome + token/cost estimates.
- CLI: extend `metagit run` with `show|replay|export` (keep existing `open|close|list`); MCP parity.
- Safety: append-only by default; redaction hooks for secrets.
- Optional DocumentStore backend under `harness.runs` (RFC-0015).

**Acceptance:**
- Every `aos next --commit` + subsequent task completion writes a run record.
- `metagit run replay <id> --dry-run` reconstructs control-loop steps.
- Docs `docs/reference/run-ledger.md` + modality parity.
- Tests cover concurrent agents writing to the same ledger.

**Suggested PR split:** (1) schema + local writer gaps / report-only, (2) CLI/MCP read surface, (3) AOS/task/merge integration, (4) optional remote DocumentStore.

### RFC-0019: Failure Recovery & Control-Loop Resilience

**Problem:** ACL leases, worktrees, claims, and task nodes can be left inconsistent after crashes or partitions.

**Proposed:**
- Expand `metagit aos doctor` with recovery recipes (expire leases, GC worktrees, orphan claims, stuck task nodes).
- Add `metagit aos recover --agent-id …` (gated, `--yes` required) for safe GC + status transitions only.
- Heartbeat / lease renewal helpers for long-running agents (align with RFC-0017 heartbeat).
- Emit events into the shared coordination events feed.

**Acceptance:**
- Doctor findings include actionable recovery commands.
- Recover never silently deletes claims or cancels merges without explicit flags.
- Integration tests simulate agent crash mid-lease.
- Docs update control-loop sections in `aos.md` + `agent-coordination.md`.

**PR split:** doctor enhancements → recover command → heartbeat helpers.

### RFC-0020: Discovery & Onboarding Surfaces

**Design:** [2026-08-27-rfc-0020-discovery-onboarding-design.md](2026-08-27-rfc-0020-discovery-onboarding-design.md)

**Proposed:** `metagit workspace health` / `summary --json` readiness score; optional `metagit init --agent-optimized`; more reference manifests + Hermes/Cursor examples.

**Acceptance:** Structured JSON usable by agents; init path documented; ≥1 additional example workspace committed.

### RFC-0021: Multi-Agent Scenario Test Harness

**Design:** [2026-08-27-rfc-0021-multi-agent-scenarios-design.md](2026-08-27-rfc-0021-multi-agent-scenarios-design.md)

**Shipped MVP:** `tests/scenarios/` harness + README with five core scenarios (lease contention, claim overlap, concurrent `aos next`, crash/doctor GC, CAS conflict) plus optional run-ledger concurrent writers. Full `aos recover` assertion remains deferred to RFC-0019 wiring; HTTP stub CAS is `@pytest.mark.nightly`.

**Proposed (remaining):** PR CI wiring in prepush gate; nightly HTTP/subprocess variants; ≥10 consecutive flake-free CI runs.

**Acceptance:** ≥5 deterministic scenarios in CI; harness docs; structured failure diagnostics (timeline + snapshot + suggested doctor commands).

### RFC-0022: Policy Engine for Mutating Classes

**Design:** [2026-08-27-rfc-0022-policy-engine-design.md](2026-08-27-rfc-0022-policy-engine-design.md)

**Proposed:** Declarative `policy` (or extend routing promotion policy) evaluated before ACL bind, merge integrate, catalog mutation, remote state writes. CLI `metagit policy eval --action … --json`. Default-deny only for high-risk classes when `METAGIT_AGENT_MODE=true` after happy-path tests stay green. Audit into run ledger.

### Secrets & Redaction (incremental PR)

**Design:** [2026-08-27-secrets-redaction-hardening-design.md](2026-08-27-secrets-redaction-hardening-design.md)

Expand gitleaks / secrets analysis; centralize `SecretRedactor` from run ledger `redaction.py`; extend to context packs, MCP resources, config preview; document safe token-handling patterns.

### RFC-0023: Workspace Federation & Org-Scale Identity

**Design:** [2026-08-27-rfc-0023-federation-design.md](2026-08-27-rfc-0023-federation-design.md)

Formalize org + workspace IDs; federated read-only catalog; `metagit workspace link` / `federation status`. Target scale: **dozens** of workspaces first. Coordinate with plane RFC-0016.

### RFC-0024: Plugin / Detector / Skill Extension Points

**Design:** [2026-08-27-rfc-0024-plugins-design.md](2026-08-27-rfc-0024-plugins-design.md)

Stable protocols for custom detectors, context-pack contributors, skill packaging; optional entry-point discovery; example external package under `examples/metagit-plugin-demo/`.

### RFC-0025: Workspace Index & Grep Scaling

**Design:** [2026-08-27-rfc-0025-workspace-index-design.md](2026-08-27-rfc-0025-workspace-index-design.md)

Optional on-disk index under `.metagit/index/`; ripgrep remains grep backend; benchmarks for 50/200-repo fixtures; corrupt index safely ignored.

## Suggested execution order

1. **Immediate**
   - ~~Agent OS Quickstart narrative PR.~~ **Done** — `docs/agents-quickstart.md`.
   - Start RFC-0017 run-evidence completion (schema + local writer gaps; report-only).
2. **Next**
   - RFC-0019 doctor/recover.
   - RFC-0021 scenario harness (can parallel).
   - RFC-0020 health/summary.
3. **Then**
   - RFC-0022 policy + secrets redaction PR.
   - Begin RFC-0023 design (with plane 0016).
4. **Later**
   - RFC-0024 plugins.
   - RFC-0025 indexing.

## Locked decisions

| # | Decision |
|---|----------|
| D1 | New reliability RFCs start at **0019**; never reuse 0016–0018. |
| D2 | Run ledger default remains local routing storage (`RoutingConfig.runs`); optional plane `harness.runs` / DocumentStore is opt-in. |
| D3 | Prefer report-only / dry-run first; mutating paths behind explicit flags (`--yes`, `--commit`, `--apply`). |
| D4 | Agent-mode default-deny is **not** flipped globally until high-risk class ceilings are proven against happy-path tests. |
| D5 | Federation designs for dozens of workspaces first; hundreds wait on catalog backend + indexing. |
| D6 | Never launch models from core AOS paths (existing invariant). |
| D7 | `METAGIT_AGENT_MODE` stays non-interactive and JSON-first. |

## Cross-cutting requirements (every RFC/PR)

- Update `scripts/modality-parity.yml` and regenerate the feature registry.
- Keep CLI / MCP / Web / docs / skills parity for agent-facing surfaces.
- Add or extend corresponding skill(s) when the surface is agent-facing.
- Document in `docs/reference/` and link from `docs/agents.md` + `llms.txt`.
- Run `task qa:prepush` and GitNexus impact / `detect_changes` before claiming done.
- Update this index + `.mex/ROUTER.md` when a package ships; bump `last_updated`.

## Document conventions

Each **design** includes: Summary, Goals, Non-Goals, Architecture, Interfaces, Persistence, Acceptance, Dependencies, Decisions (locked), Open questions (if any).

Each **plan** lives under `docs/superpowers/plans/` and follows the writing-plans skill format.

Public `docs/reference/rfc-00NN*` stubs are not added until that RFC ships.
