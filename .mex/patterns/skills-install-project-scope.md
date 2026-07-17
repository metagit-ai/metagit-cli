---
name: skills-install-project-scope
description: Ensure metagit skills/mcp --scope project and Hermes HERMES_HOME targeting install correctly.
edges:
  - target: ../context/conventions.md
    condition: when changing CLI installer path resolution
last_updated: 2026-07-17
---

# Skills / MCP project-scope + Hermes install roots

## When

Changing `metagit skills install` or `metagit mcp install` destination paths, debugging installs that land under a nested cwd, or Hermes installs that miss the active gateway home.

## Steps

1. Keep library helpers (`install_skills_for_targets`, `install_mcp_for_targets`) cwd-relative unless callers pass `project_root` — `AgentProfileService` chdirs into repo mounts that may not be git roots.
2. CLI `--scope project` must call `resolve_project_install_root()` (nearest `.git` parent, else cwd) and pass that as `project_root`.
3. Hermes user-scope paths must use `resolve_hermes_home()` / `HERMES_HOME` (default `~/.hermes`), not `~/.config/hermes`.
4. Hermes MCP must merge YAML `$HERMES_HOME/config.yaml` → `mcp_servers` and launch the installed `metagit` binary (never default `uvx metagit-cli`).
5. Add/extend tests for nested-cwd project scope and `HERMES_HOME` skill/MCP installs.
6. Document paths in `docs/skills.md` / `docs/reference/metagit-agent.md` and CHANGELOG Fixed.

## Done when

- Dry-run from a subdirectory prints `…/<repo>/.cursor/skills` (or equivalent vendor path), not `…/<subdir>/.cursor/skills`.
- With `HERMES_HOME=/tmp/h`, Hermes skills land in `/tmp/h/skills` and MCP updates `/tmp/h/config.yaml` without `uvx`.
- Unit + CLI skills/MCP installer tests pass.
