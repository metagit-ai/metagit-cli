---
name: bootstrap-metagit-config
description: Create or repair `.metagit.yml` using model validation and optional MCP sampling.
triggers:
  - "bootstrap config"
  - "generate .metagit.yml"
  - "metagit config invalid"
edges:
  - target: context/setup.md
    condition: when environment/command prerequisites impact config generation
  - target: context/stack.md
    condition: when config/schema model constraints need confirmation
  - target: context/mcp-runtime.md
    condition: when bootstrap is performed through MCP tool calls and sampling flow
last_updated: 2026-05-05
---

# Bootstrap Metagit Config

## Context
Use this when `.metagit.yml` is missing or invalid, or when onboarding a new workspace. Relevant modules are `metagit.core.config.manager` and MCP bootstrap services.

## Steps
1. Check for existing `.metagit.yml` and validate (`uv run metagit config validate`).
2. If missing/invalid, create baseline config using manager/create flow or bootstrap wrapper.
3. Re-validate using model-driven load path (not string-only checks).
4. If running through MCP, use `metagit_bootstrap_config` and verify returned mode (`plan_only` vs `sampled`).
5. Keep writes explicit when replacing existing config.

## Gotchas
- Writing guessed YAML without model validation creates downstream gate failures.
- Overwriting a valid `.metagit.yml` silently can erase workspace repo mappings.
- Sampling output must still pass strict config model validation before use.

## Verify
- [ ] `.metagit.yml` loads through `MetagitConfigManager.load_config()` without exception.
- [ ] Workspace section shape is valid for project/repo operations.
- [ ] MCP gate moves to active when expected.
- [ ] `task lint` and relevant tests pass.

## Debug
- If validation fails: inspect exact model error path and adjust YAML fields/types.
- If gate remains inactive: verify resolver root points to intended workspace directory.
- If sampling output fails repeatedly: run plan-only mode and patch fields manually.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
