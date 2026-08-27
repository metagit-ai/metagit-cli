# RFC-0020: Discovery & Onboarding Surfaces — Design

**Status:** Proposed  
**Date:** 2026-08-27  
**Series:** [Agent Reliability series index](2026-08-27-agent-reliability-series-index.md)  
**Depends on:** Shipped MCP Phase 3 workspace intelligence, context packs, `metagit init` templates, docs quickstart (`examples/agent-aos-loop/`)  
**Plan:** (pending — `docs/superpowers/plans/2026-08-27-rfc-0020-discovery-onboarding.md`)  
**Related:** [MCP Phase 3 workspace intelligence](2026-05-15-mcp-phase3-workspace-intelligence-design.md) · [Context packs](2026-05-21-context-packs-design.md) · skill `metagit-agent-access`

## Summary

Agents onboarding to a metagit workspace currently scatter across MCP-only health checks, context-pack tiers, AOS doctor, and ad-hoc `workspace list` output. **RFC-0020 adds a unified, JSON-first discovery surface:** CLI `metagit workspace health` and `metagit workspace summary --json` with an explicit **readiness score**, plus optional **`metagit init --agent-optimized`** scaffolding for `llms.txt`, agent-access markers, and manifest session blocks. Reuse existing `WorkspaceHealthService` and agent-access optimizer logic; do not introduce new persistence or engines.

## Goals

1. **CLI parity** for workspace maintenance health already exposed as MCP `metagit_workspace_health_check` and resource `metagit://workspace/health`.
2. **`metagit workspace summary --json`** — one structured payload agents can consume at session start: gate status, maintenance health rollup, workspace map stats, per-repo agent-surface signals, and a **composite readiness score** with explainable dimensions.
3. **Readiness score** — machine-readable 0–100 integer plus per-dimension breakdown and blocking `findings[]`; suitable for automation (skip work, escalate, or proceed).
4. **`metagit init --agent-optimized`** — opt-in flag (works with `--template`, `--kind`, `--minimal`) that scaffolds agent onboarding artifacts without overwriting human-authored content.
5. **Documentation & examples** — document commands in `docs/agents.md` and `docs/agents-quickstart.md`; add ≥1 reference workspace beyond `examples/agent-aos-loop/` (Hermes or Cursor-oriented minimal manifest).
6. **Modality parity** — register `workspace_health` and `workspace_summary` in feature registry; MCP tool + resource for summary; bundled skill pointer updates.

## Non-Goals

- Replacing context packs, AOS doctor, or the MCP resource ladder.
- New on-disk indexes (defer to RFC-0025).
- Federation / org catalog (RFC-0023).
- Auto-sync, auto-clone, or mutating health remediation (report-only; existing prune/sync commands remain separate).
- Full agent-access editorial pass inside `init` (script scaffold only; subagent flow stays in `metagit-agent-access` skill).
- Web UI redesign (wire existing ops panel to summary endpoint later if cheap).

## Architecture

Thin composition over shipped services — no new engines.

```text
metagit workspace health|summary [--json]
              │
              ▼
     WorkspaceDiscoveryService (new, thin)
       ├─► WorkspaceHealthService.check()     (existing)
       ├─► WorkspaceIndexService.build_index() (existing)
       ├─► WorkspaceGate.evaluate()            (existing)
       ├─► RepoCardService (optional, summary)  (existing)
       └─► AgentAccessAudit (read-only)         (from metagit-agent-access script)
```

**Package placement:**

| Module | Role |
|--------|------|
| `src/metagit/core/workspace/discovery_service.py` | Orchestrates health + summary + readiness scoring |
| `src/metagit/core/workspace/discovery_models.py` | Pydantic result types (`WorkspaceSummaryResult`, `ReadinessScore`, …) |
| `src/metagit/core/mcp/services/workspace_health.py` | Unchanged implementation; imported by discovery service (relocate to `core/workspace/` only if import cycles force it — prefer import-as-is in v1) |
| `src/metagit/cli/commands/workspace.py` | Add `health` and `summary` subcommands |
| `src/metagit/core/init/service.py` | Honor `--agent-optimized` post-manifest write |

**Relationship to existing surfaces:**

| Surface | RFC-0020 role |
|---------|----------------|
| `metagit context pack --tier N` | Summary **references** tier-0 map counts; does not embed full pack (token lean) |
| `metagit aos doctor` | Summary may include **lightweight** coordination hints (lease/worktree counts) when cheap; full recovery stays in RFC-0019 |
| MCP `metagit_workspace_health_check` | Same underlying health payload as CLI `workspace health` |
| Prompt `health-preflight` | Update template to cite `metagit workspace summary --json` as primary |
| `examples/agent-aos-loop/` | Remains AOS loop example; new example focuses discovery/onboarding |

## Interfaces

### CLI

```bash
# Maintenance health (parity with MCP health check)
metagit workspace health [--json]
  [--project PROJECT]
  [--no-git-status | --check-git-status]
  [--no-stale-branches | --check-stale-branches]
  [--no-gitnexus | --check-gitnexus]
  [--no-dependencies | --check-dependencies]
  [-c PATH | --definition PATH]

# Discovery + readiness (new)
metagit workspace summary [--json]
  [--project PROJECT]
  [--include-cards]          # attach tier-1 repo cards (default false — lean)
  [--include-coordination]   # aos status subset (default true when aos importable)
  [-c PATH | --definition PATH]

# Init scaffolding (extends existing init)
metagit init [TARGET] --agent-optimized [--template T | --kind K | --minimal] …
```

**Human text mode:** `workspace health` prints recommendation count + top 5 actions (severity-sorted). `workspace summary` prints readiness score, grade label, and top blockers.

### MCP (ACTIVE-gated)

| Tool | Purpose |
|------|---------|
| `metagit_workspace_health_check` | **Existing** — ensure JSON shape stable; document CLI equivalent |
| `metagit_workspace_summary` | **New** — same payload as `workspace summary --json` |

| Resource | Purpose |
|----------|---------|
| `metagit://workspace/health` | **Existing** |
| `metagit://workspace/summary` | **New** — summary without full repo cards unless `?cards=1` |

### JSON shapes (v1)

#### `workspace health`

Re-export existing `WorkspaceHealthResult` (`ok`, `workspace_root`, `summary`, `repos[]`, `recommendations[]`). CLI/MCP must share identical serialization (already true for MCP/web).

#### `workspace summary`

```json
{
  "generated_at": "2026-08-27T19:00:00Z",
  "workspace_root": "/path/to/workspace",
  "gate": { "state": "active", "reason": null },
  "map": {
    "projects": 2,
    "repos_total": 5,
    "repos_present": 4,
    "repos_missing": 1
  },
  "health": {
    "ok": false,
    "critical_count": 0,
    "warning_count": 2,
    "top_actions": ["clone", "sync"]
  },
  "agent_surfaces": {
    "manifest_has_agent_instructions": true,
    "umbrella_has_agents_md": true,
    "umbrella_has_llms_txt": false,
    "repos_audited": 4,
    "repos_with_agents_md": 2,
    "repos_with_llms_txt": 1,
    "repos_with_readme_marker": 0
  },
  "coordination": {
    "available": true,
    "acl_leases_active": 0,
    "ready_tasks": 1,
    "doctor_findings": 0
  },
  "readiness": {
    "score": 72,
    "grade": "fair",
    "dimensions": {
      "gate_active": { "score": 100, "weight": 0.25, "met": true },
      "repos_present": { "score": 80, "weight": 0.25, "met": true },
      "maintenance_clear": { "score": 60, "weight": 0.25, "met": false },
      "agent_surfaces": { "score": 50, "weight": 0.25, "met": false }
    },
    "blockers": [
      { "code": "missing_clone", "severity": "warning", "message": "…", "project_name": "demo", "repo_name": "api" }
    ],
    "suggested_commands": [
      "metagit project sync --project demo",
      "metagit init --agent-optimized  # on repos missing AGENTS.md"
    ]
  },
  "quickstart_uri": "docs/agents-quickstart.md"
}
```

**Readiness scoring (locked v1 weights):**

| Dimension | Weight | Scoring rule |
|-----------|--------|--------------|
| `gate_active` | 25% | 100 if gate ACTIVE; 0 if inactive |
| `repos_present` | 25% | `100 * repos_present / max(repos_total, 1)` |
| `maintenance_clear` | 25% | 100 if health `ok`; subtract 30 per critical recommendation, 10 per warning (floor 0) |
| `agent_surfaces` | 25% | Umbrella: 40 pts manifest `agent_instructions`, 30 pts `AGENTS.md`, 30 pts `llms.txt`; repo average adds up to 40 pts scaled by `% repos with AGENTS.md or llms.txt or README agent-access marker` |

**Grade bands:** `excellent` ≥90, `good` ≥75, `fair` ≥50, `poor` <50.

Reuse terrain web heuristic for per-repo file probes (`AGENTS.md`, `llms.txt`, `docs/`, README marker) via shared helper extracted from `terrain_service._agent_state` and `optimize_agent_access.py` audit (read-only, no subprocess).

### `metagit init --agent-optimized`

Runs **after** manifest write succeeds (template or minimal kind). Idempotent; never overwrites existing agent artifacts unless `init --force` (existing init semantics).

**Actions (target directory = init target):**

1. If no `AGENTS.md` — write from bundled fragment (`agent-standard` / new `agent-optimized` template dir) with session-start block pointing to `docs/agents-quickstart.md` when docs exist.
2. If no `llms.txt` — write minimal index (≤80 lines) listing manifest path, agents docs, skills install.
3. If `README.md` exists and lacks `<!-- agent-access:start` — inject hidden HTML comment block (same convention as `metagit-agent-access` skill).
4. If manifest lacks top-level `agent_instructions` — append minimal 5-step session block (context pack → summary → aos next); **do not** replace non-empty instructions.
5. For `kind: umbrella` — ensure `examples/` pointer or inline note to `agent-aos-loop` in generated `AGENTS.md` when repo is metagit-cli itself is not assumed (generic text).

**Interaction with templates:**

| Init path | `--agent-optimized` behavior |
|-----------|----------------------------|
| `--template hermes-orchestrator` | Hermes already has rich `agent_instructions`; only scaffold missing `llms.txt` / README marker / umbrella `AGENTS.md` |
| `--template application` | Full scaffold on single-repo app |
| `--kind umbrella --minimal` | Scaffold + inject minimal umbrella `agent_instructions` if empty |
| Re-run on valid manifest | No-op for agent files (same as init idempotency); report `agent_optimized: skipped_existing` in JSON when `--json` on init |

Delegate file writes to existing `optimize_agent_access.py` logic (importable functions) to avoid duplication.

## Persistence

None new. All inputs are computed from manifest, workspace index, git inspection, and on-disk file probes.

## Skills & docs

| Artifact | Change |
|----------|--------|
| `docs/agents.md` | Add **Discovery & readiness** section with `workspace health`, `workspace summary`, `init --agent-optimized` |
| `docs/agents-quickstart.md` | Step 2 (Health) adds `metagit workspace summary --json` before/alongside aos doctor |
| `docs/reference/workspace-discovery.md` | **New** when RFC ships (score dimensions, JSON schema, MCP parity) |
| Skill `metagit-workspace-scope` | Session start: summary before tier-2 pack escalation |
| Skill `metagit-agent-access` | Cross-link init flag vs on-demand `--apply` |
| Skill `metagit-mcp-resources` | Add L2 `metagit://workspace/summary` |
| Prompt `health-preflight` | Prefer summary command over manual list steps |
| `llms.txt` / `AGENTS.md` (this repo) | Modality markers when implemented |

**Example workspaces (acceptance):**

| Path | Purpose |
|------|---------|
| `examples/agent-aos-loop/` | **Existing** — AOS control loop |
| `examples/agent-discovery/` | **New** — minimal umbrella demonstrating `workspace summary --json` + init `--agent-optimized` README |
| `examples/hermes-orchestrator/` | **Existing** — link from discovery example as multi-repo controller pattern |

Optional follow-up (not blocking RFC): `examples/cursor-agent-workspace/` with `.cursor/mcp.json` snippet referencing `metagit mcp install`.

## Acceptance

- `metagit workspace health --json` from manifest root returns the same core fields as `metagit_workspace_health_check` for equivalent flags.
- `metagit workspace summary --json` returns `readiness.score`, `readiness.dimensions`, and `readiness.blockers` on fixtures with missing clone + missing `AGENTS.md`.
- Readiness score is deterministic for a fixed workspace fixture (unit tests with tmp_path).
- `metagit init ./tmp --agent-optimized --kind application --no-prompt` creates `AGENTS.md` and `llms.txt` when absent; second run does not duplicate README HTML markers.
- MCP `metagit_workspace_summary` and resource `metagit://workspace/summary` match CLI JSON.
- `docs/agents.md` documents all three entry points; quickstart health step references summary.
- ≥1 new example under `examples/agent-discovery/` committed with README runnable commands.
- `scripts/modality-parity.yml` entries `workspace_health`, `workspace_summary`; registry regenerated.
- Agent mode: all commands support `--json`, exit 0 on report-only success even when `readiness.score < 50` (non-zero exit reserved for invalid manifest / gate errors only).

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| MCP Phase 3 `WorkspaceHealthService`, context packs, init templates, agent-access skill | Faster agent onboarding; input to RFC-0021 scenario fixtures |
| Docs quickstart + `examples/agent-aos-loop/` | Narrative continuity |
| RFC-0019 (soft) | Summary `--include-coordination` may surface doctor finding counts; full recover recipes stay in 0019 |

## Suggested PR split

1. **Core + CLI:** `discovery_models`, `discovery_service`, readiness scorer, `workspace health|summary` commands, unit tests.
2. **MCP + resource:** `metagit_workspace_summary`, `metagit://workspace/summary`, modality parity.
3. **Init flag:** `--agent-optimized` wiring + init tests.
4. **Docs + examples:** agents.md, quickstart, `examples/agent-discovery/`, prompt/skill updates.

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | **Report-only** — health/summary never mutate disk or git state. |
| D2 | **Reuse** `WorkspaceHealthService` — no second health implementation. |
| D3 | Readiness is a **weighted composite** with documented dimensions; agents rely on `blockers[]` and `suggested_commands[]`, not score alone. |
| D4 | Summary default is **lean** (no full repo cards); `--include-cards` opt-in. |
| D5 | `init --agent-optimized` **never overwrites** existing agent artifacts without `--force`. |
| D6 | Agent-access file writes go through **shared optimizer functions**, not duplicated templates in init. |
| D7 | CLI command names: `workspace health`, `workspace summary` (not top-level `metagit health`). |
| D8 | Exit code 0 for “unhealthy but valid workspace” reports; non-zero only for config/gate/usage errors. |

## Open questions

1. Should summary embed a **truncated tier-0 map** inline?  
   **Recommendation:** no — include counts only; agents fetch `context pack --tier 0` when needed.
2. Should readiness include **PyPI version freshness** (`metagit version check`)?  
   **Recommendation:** optional `readiness.meta.cli_version_outdated: bool` in v1.1; not in initial score weight.
3. Relocate `WorkspaceHealthService` from `core/mcp/services/` to `core/workspace/`?  
   **Recommendation:** defer unless import cycles appear; document MCP layer as thin wrapper.
