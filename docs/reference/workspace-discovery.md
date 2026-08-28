---
title: Workspace discovery
---

<!-- modality:workspace_health -->
<!-- modality:workspace_summary -->

# Workspace discovery & readiness (RFC-0020)

JSON-first surfaces for agent onboarding. Report-only — no disk or git mutations.

## Commands

```bash
metagit workspace health --json
metagit workspace summary --json
```

`workspace health` mirrors MCP `metagit_workspace_health_check` / resource
`metagit://workspace/health`.

`workspace summary` returns a lean readiness payload: gate, map counts, health
rollup, agent-surface probes, optional coordination hints, and a composite
`readiness.score` (0–100) with dimensions and blockers.

Exit code is **0** for unhealthy-but-valid workspaces; non-zero only for
invalid manifest / usage errors.

## Readiness dimensions (v1)

| Dimension | Weight | Rule |
|-----------|--------|------|
| `gate_active` | 25% | 100 if gate ACTIVE else 0 |
| `repos_present` | 25% | `100 * present / max(total, 1)` |
| `maintenance_clear` | 25% | Start 100; −30 per critical, −10 per warning |
| `agent_surfaces` | 25% | Umbrella (instructions/AGENTS.md/llms.txt) × 0.6 + up to 40 × repo surface coverage |

Grades: `excellent` ≥90, `good` ≥75, `fair` ≥50, `poor` <50.

## See also

- [Agents guide](../agents.md)
- [Agents quickstart](../agents-quickstart.md)
- Design: [RFC-0020](../superpowers/specs/2026-08-27-rfc-0020-discovery-onboarding-design.md)
