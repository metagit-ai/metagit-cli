---
name: modality-feature-registry
description: Register user-facing features across CLI, MCP, Web, docs, and skills using modality-parity.yml.
last_updated: 2026-07-06
---

# Modality feature registry pattern

## When to use

Adding or changing any user-facing capability (CLI command group, MCP tool, web route, agent workflow).

## Steps

1. Add or update an entry in `scripts/modality-parity.yml`:
   - `id`, `description`, optional `service`, `reference_doc`
   - `surfaces.cli|mcp|web|documentation|skills` with `markers` (`path` + `contains`)
2. Place `<!-- modality:FEATURE_ID -->` in primary reference doc and bundled skills.
3. Run `task generate:modality-registry` (included in `task generate:schema`). The generated registry links `scripts/modality-parity.yml` via a GitHub blob URL (MkDocs `--strict` cannot resolve relative paths outside `docs/`).
4. Run `task qa:prepush` — `check_modality_parity.py` validates markers and doc anchors.

## Verify

- `docs/reference/modality-feature-registry.md` table includes the feature
- `metagit skills list` shows updated bundled skill when applicable
