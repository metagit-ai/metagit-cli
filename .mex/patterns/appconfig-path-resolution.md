---
name: appconfig-path-resolution
description: Resolve AppConfig YAML files without treating workspace.path as the config path.
triggers:
  - "appconfig defaults to .metagit"
  - "metagit.config.yaml missing"
  - "config_path ./.metagit"
  - "user ~/.config/metagit/config.yml"
edges:
  - target: patterns/project-cli-resolution.md
    condition: when project list/select is wrong because workspace.path or default_project is mis-resolved
  - target: context/architecture.md
    condition: when tracing CLI bootstrap into AppConfig load
last_updated: 2026-09-18
---

# AppConfig path resolution

## Context
`metagit -c` defaults to `metagit.config.yaml`. That file is **AppConfig**, not the workspace sync folder. `workspace.path` (schema default `./.metagit`) is where clones live. Do not store it in `ctx.obj["config_path"]`.

## Steps
1. Detect `-c` with `detect_cli_config_file()` (`appconfig` / `manifest` / `missing` / `invalid`).
2. Resolve the YAML file with `resolve_cli_bootstrap()`:
   - Explicit AppConfig file wins.
   - Manifest: sidecar `metagit.config.yaml` then `.yml` next to the manifest, then user config, then bundled `DEFAULT_CONFIG`.
   - Missing local file: sibling `.yml`/`.yaml`, then `user_appconfig_paths()` (`$XDG_CONFIG_HOME/metagit/config.yml` else `~/.config/metagit/config.yml`, then `.yaml`), then bundled default.
3. Put the **resolved YAML path** in `ctx.obj["config_path"]`. `definition_path` is the manifest when `-c` was a `.metagit.yml`.
4. `project` / `workspace` groups may overwrite `config_path` with the manifest path; that is intentional (see `cli-tui-hub.md`).

## Gotchas
- `resolve_cli_bootstrap` returns `(config, definition_path, appconfig_path)` — three values. Do not unpack two and then guess the file from `cfg.workspace.path`.
- `AppConfig.load()` with no path uses `default_user_appconfig_path()`, not the bundled package file. CLI missing-file fallback uses the bundled file when no user file exists.
- `metagit.config.yml` is a valid local alias; `~/.config/metagit/config.yml` is the user-level file documented for providers and sharing-state.

## Verify
- [ ] `tests/cli/test_config_path.py` and `tests/cli/commands/test_appconfig.py` pass.
- [ ] Isolated cwd without local appconfig: `metagit appconfig info` does not print `config_path: ./.metagit`.
- [ ] `metagit appconfig validate` succeeds against the bundled or user YAML file.

## Debug
- Symptom `Validating configuration file: ./.metagit` then exit 1: `ctx.obj["config_path"]` was set to `workspace.path`.
- User tokens ignored: check `~/.config/metagit/config.yml` exists and local `metagit.config.yaml` is not shadowing it.
