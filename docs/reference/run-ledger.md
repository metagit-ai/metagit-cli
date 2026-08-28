---
title: Run ledger
---

<!-- modality:run_ledger -->

# Run ledger (routing evidence)

Durable records of agent/control-loop executions. Built on the routing engine
(`metagit.core.routing`) with one YAML file per run under
`routing.runs` (default `knowledge/requests/runs`).

## Commands

```bash
metagit run open --class REQ-X --actor agent-1 --json
metagit run close --id RUN-… --outcome landed --json
metagit run list --json
metagit run show RUN-… --json
metagit run replay RUN-… --dry-run --json
metagit run export --json
```

Show / replay / export redact secret-like strings by default (`--no-redact` to skip).

## Control-loop steps

`RunEvidence.steps[]` captures ordered events (`aos_next`, `acl_bind`,
`context_compile`, `task`, `mutation`, …). Append via
`RoutingService.append_step`.

`aos next --commit` best-effort opens a run under system class `REQ-AOS-NEXT`
when a `routing:` block is present and returns `run_id` on the JSON envelope.

## MCP

ACTIVE-gated:

| Tool | Purpose |
|------|---------|
| `metagit_run_list` | List/export runs |
| `metagit_run_show` | Show one run |
| `metagit_run_replay` | Reconstruct steps (`dry_run`) |

## See also

- [Agent OS quickstart](../agents-quickstart.md)
- [Agent Operating System](aos.md)
- Design: [RFC-0017 run evidence completion](../superpowers/specs/2026-08-27-rfc-0017-run-evidence-completion-design.md)
