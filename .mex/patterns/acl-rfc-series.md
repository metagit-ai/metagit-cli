---
name: acl-rfc-series
description: Navigate or extend the RFC-0007–0013 agent coordination series (designs and implementation plans).
edges:
  - target: agent-coordination-acl.md
    condition: when implementing shipped ACL primitives
  - target: ../context/architecture.md
    condition: when placing new packages under src/metagit/core
last_updated: 2026-07-09
---

# ACL RFC series (0008–0013)

## When to use

Starting the next coordination MR, or updating deferred RFC scope after RFC-0007.

## Do

1. Read the series index first: `docs/superpowers/specs/2026-07-09-acl-rfc-series-index.md`.
2. Implement only the RFC for the current MR; keep shared locks (modality, local JSON, lease naming).
3. For RFC-0008 / RFC-0010 use the fuller TDD plans; for 0011–0013 expand phased plans into TDD steps at MR start.
4. Treat RFC-0013 as composition-only — no new engines.

## Don't

- Don't implement 0011–0013 inside the 0010 MR.
- Don't implement 0009–0013 inside the 0008 MR.
- Don't add public `docs/reference/rfc-000N` stubs until that RFC ships.
- Don't introduce SQLite/Postgres unless a specific RFC explicitly opens it.

## Verify

```bash
ls docs/superpowers/specs/2026-07-09-rfc-000*.md
ls docs/superpowers/plans/2026-07-09-rfc-000*.md
```
