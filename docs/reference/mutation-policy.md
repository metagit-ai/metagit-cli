---
title: Mutation policy
---

<!-- modality:mutation_policy -->

# Mutation policy (RFC-0022 MVP)

Report-only evaluation of whether an action class is allowed under the current
policy and `METAGIT_AGENT_MODE`.

## CLI

```bash
metagit policy eval --action merge_integrate --json
```

Actions: `sync`, `merge_integrate`, `claim_declare`, `claim_release`,
`catalog_edit`, `remote_state_write`, `acl_bind`, `aos_recover`, `run_open`.

In agent mode, high-risk classes default to **deny** unless an explicit allow
rule is configured (AppConfig wiring follows in a later slice).

## See also

- Series index: [agent reliability](../superpowers/specs/2026-08-27-agent-reliability-series-index.md)
- Routing promotion ceilings remain separate (`metagit lane eval`).
