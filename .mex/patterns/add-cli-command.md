---
name: add-cli-command
description: Add or extend a metagit CLI command with core logic boundaries and test coverage.
triggers:
  - "add command"
  - "click command"
  - "new subcommand"
edges:
  - target: context/architecture.md
    condition: when deciding where command logic belongs vs core service logic
  - target: context/conventions.md
    condition: when implementing command/module naming and verify checklist items
  - target: patterns/debug-mcp-runtime.md
    condition: when the new command affects MCP runtime behavior and tests fail
last_updated: 2026-05-05
---

# Add CLI Command

## Context
Load `context/architecture.md` and `context/conventions.md` first. Confirm whether the task is a new command file under `src/metagit/cli/commands/` or an extension of existing command behavior.

## Steps
1. Create or update command module in `src/metagit/cli/commands/`.
2. Keep handler thin: instantiate/call core service/manager classes in `src/metagit/core/*`.
3. Register command in `src/metagit/cli/main.py` if it is a top-level subcommand.
4. Add command tests under `tests/cli/commands/` and integration tests if behavior crosses modules.
5. Run focused tests first, then project lint.

## Gotchas
- Putting substantial logic directly in Click handlers increases duplication and weakens testing boundaries.
- Forgetting registration in `main.py` makes command exist in code but unavailable in CLI.
- Command output contracts should remain stable (especially in automation-facing flows).

## Verify
- [ ] Command appears in `uv run metagit --help` or relevant group help output.
- [ ] Unit/CLI tests cover new path.
- [ ] Core behavior test exists if command bridges multiple services.
- [ ] `task lint` passes.

## Debug
- If command is missing: check `cli.add_command(...)` registration in `src/metagit/cli/main.py`.
- If context/logger missing: verify `@click.pass_context` and `ctx.obj` usage path.
- If tests hang on MCP command: use `--status-once` in test paths.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
