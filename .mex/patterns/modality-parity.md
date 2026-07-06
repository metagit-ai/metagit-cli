# Modality parity (CLI, MCP, Web)

## Rule

Every **user-facing workspace capability** must share one core service and expose thin adapters per modality:

| Modality | Adapter location | Contract |
|----------|------------------|----------|
| CLI | `src/metagit/cli/commands/` | Click flags + human prompts |
| MCP | `src/metagit/core/mcp/services/` + `runtime.py` | JSON tool schema |
| Web | `src/metagit/core/web/*_handler.py` + `web/src/` | `/v3` JSON + SPA |
| HTTP v2 | `src/metagit/core/api/` | Catalog/layout/grep only (not all features) |

Adapters validate input, call the shared service, return `model_dump(mode="json")` shapes. **Never duplicate business logic** (approval side effects, manifest apply, discovery filters) in a single modality.

## When adding a feature

1. Implement core logic under `src/metagit/core/<area>/`.
2. Wire **CLI + MCP + Web** in the same PR when the feature is operator-facing (Config Studio–only schema edits are the exception).
3. Add a row to `scripts/modality-parity.yml` with `markers` per surface (file path + substring).
4. Run `task generate:modality-registry` to refresh `docs/reference/modality-feature-registry.md`.
5. Add unit tests for the service **and** at least one adapter test per modality touched.
6. Run `task qa:prepush` (regenerates the registry, then runs `modality_parity` check).

See also: [modality-feature-registry.md](modality-feature-registry.md) for the docs/skills flow-down checklist.

## Shared orchestrators

Side effects that must run after an approval or apply step belong in a named orchestrator (example: `ApprovalResolveOrchestrator`), invoked from CLI **and** web — not copied into handlers.

## Registry

`scripts/modality-parity.yml` lists features and required markers. `scripts/generate_modality_registry.py` builds the human-readable matrix at `docs/reference/modality-feature-registry.md`. `scripts/check_modality_parity.py` fails CI when a declared marker is missing. This is intentionally lightweight (substring checks); expand entries as features ship.

## Exceptions (document in YAML)

- Read-only HTTP v2 routes without MCP equivalents (grep, catalog).
- Agent-only aliases (`metagit workspace import`) that delegate to the same runner as CLI.
- Config Studio fields with no “run” action (declarative YAML only) — web edit parity is schema tree, not ops.

## Verify Checklist

- [ ] Core service has unit tests
- [ ] `scripts/modality-parity.yml` updated
- [ ] CLI/MCP/Web adapters call the same service or orchestrator
- [ ] Web route documented in `docs/reference/metagit-web.md` when adding `/v3/ops/*`
- [ ] `task qa:prepush` green
