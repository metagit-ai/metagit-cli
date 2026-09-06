---
name: component-model
description: Declare, catalog, and validate first-class repository components (RFC-0026).
triggers:
  - "component"
  - "repos[].components"
  - "RFC-0026"
  - "component catalog"
edges:
  - target: "../context/conventions.md"
    condition: when writing or reviewing component models
  - target: "component-resolution.md"
    condition: when resolving a path or looking up a component by id/name (RFC-0027)
  - target: "component-graph.md"
    condition: when declaring graph.relationships endpoints with component (RFC-0028)
  - target: "component-agent-profile.md"
    condition: when merging Component.agent_profile into EffectiveAgentProfile (RFC-0029)
  - target: "add-cli-command.md"
    condition: when adding metagit component CLI in RFC-0027
last_updated: 2026-09-06
---

# Component model (RFC-0026)

## Context

Series index: `docs/superpowers/specs/2026-09-06-rfc-0026-component-context-graph-index.md`.
Design: `docs/superpowers/specs/2026-09-06-rfc-0026-component-model-design.md`.

Package: `src/metagit/core/component/`. Validation: `metagit.core.config.component_validation.validate_components` hooked from `metagit config validate`.

## Steps

1. Keep `ProjectPath` as the git-repo type. Add nested `components: list[Component]`.
2. Do not retype top-level `paths` / `components`. Map them in `ComponentCatalog`.
3. Identity is always `project/repo/component`. Application manifests use `config.name` twice.
4. `ref`-only top-level `components[]` stay out of the catalog.
5. Validate with tests under `tests/core/component/` and `tests/core/config/test_component_validation.py`.
6. Run `task generate:schema` after model/schema changes.

## Gotchas

- Do not import `catalog` from `metagit.core.component.__init__` (circular: config.models → ProjectPath → Component package → catalog → MetagitConfig).
- `ProjectPath.frameworks` may be `None`; coerce to `[]` in `path_metadata_kwargs`.
- Filesystem existence checks run only when the repo directory exists.
- Nested prefix paths are valid; duplicate *normalized* paths are not.
- Same-repo `depends_on` cycles fail; cross-repo refs are stored only.
- `CliRunner` races UnifiedLogger; CLI validate tests should use a subprocess (see graph validate tests).
- Path/identity resolver lives in `src/metagit/core/component/resolve.py` (do not import it from package `__init__`). CLI `component` tests must use subprocess, not `CliRunner`.

## Verify

- [ ] `uv run pytest tests/core/component tests/core/config/test_component_validation.py tests/cli/commands/test_config_validate_components.py`
- [ ] `task generate:schema`
- [ ] `task qa:prepush`

## Update Scaffold

- [ ] `.mex/ROUTER.md` project state
- [ ] `docs/concepts/components.md` when operator-facing behavior changes
