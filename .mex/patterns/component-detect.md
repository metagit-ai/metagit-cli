---
name: component-detect
description: Detect filesystem component candidates and init one draft (RFC-0031 ComponentDetector).
triggers:
  - "component detect"
  - "component init"
  - "ComponentDetector"
  - "RFC-0031"
  - "already_catalogued"
edges:
  - target: "component-model.md"
    condition: when writing repos[].components[] or validating names/paths
  - target: "component-resolution.md"
    condition: when catalog rows mark already_catalogued
  - target: "add-cli-command.md"
    condition: when adding metagit component detect|init CLI
  - target: "add-mcp-tool.md"
    condition: when adding metagit_component_detect|init
  - target: "../context/conventions.md"
    condition: when writing or reviewing detector code
last_updated: 2026-09-06
---

# Component detect + init (RFC-0031)

## Context

Design: `docs/superpowers/specs/2026-09-06-rfc-0031-component-discovery-design.md`.
Plan: `docs/superpowers/plans/2026-09-06-rfc-0028-0032-remaining-series.md`.
Service: `src/metagit/core/component/detect.py` (`ComponentDetector`). Do not import from package `__init__`.
Tests: `tests/core/component/test_detect.py` (tmp_path trees; apply uses a temp umbrella whose repo path points at the tree).
CLI: `src/metagit/cli/commands/component.py` (`detect|init`). Subprocess tests, not CliRunner.
MCP: ACTIVE `metagit_component_detect` / `metagit_component_init` (`apply` bool).
Web: GET `/v3/ops/components/detect` registered before `/v3/ops/components`; POST `/v3/ops/components/init`. Shutdown servers in tests.

## Steps

1. Put scan/apply/init logic only in `ComponentDetector`. CLI/MCP/web stay thin adapters.
2. Scan root is `definition_root / repo.path` for workspace repos, or `definition_root` once for application manifests.
3. Candidate dirs: immediate children of `apps/`, `packages/`, `services/`, `libs/`, `internal/` with a marker; `infra/`, `terraform/`, `helm/`, `charts/` when they contain `.tf`, `Chart.yaml`, or `helmfile.yaml`.
4. High markers: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `*.csproj`, `uv.lock` beside `pyproject.toml`. Medium: convention dir with only `Dockerfile` / `Taskfile.yml` / `Makefile`.
5. Kind hints: `apps/` → application; `packages/` → package; `services/` → service; `libs|internal` → library; infra dirs → infrastructure. Language: `package.json` → typescript unless a better marker exists; `pyproject.toml` → python; `go.mod` → go; `Cargo.toml` → rust.
6. Skip `.git`, `node_modules`, `dist`, `build`, `.venv`, `__pycache__`, `.tox`, `vendor`, and nested marker dirs under an already-chosen candidate.
7. `already_catalogued` is true when a catalog row has the same normalized path in that project/repo. `--apply` / `apply: true` skips those and any add that would fail `validate_components`. Collect valid adds, then `MetagitConfigManager.save_config` once.
8. Detect without apply is read-only. `init PATH` drafts one `Component` (name defaults to basename). Umbrellas need `--project` and `--repo` unless there is a unique repo mapping.

## Gotchas

- Do not import `detect` from `metagit.core.component.__init__` (circular with `config.models`).
- New `detect.py` uses 4-space indent and `#!/usr/bin/env python`.
- CLI docstrings must contain the substrings `component detect` and `component init` for modality markers.
- GET detect is read-only even if a client sends `apply`; only MCP/CLI `--apply` and POST init write.
- Nested `apps/web/src/package.json` is not a candidate when `apps/web` already is.

## Verify

- [ ] `uv run pytest tests/core/component/test_detect.py tests/cli/commands/test_component_cli.py tests/core/mcp/test_component_tools.py tests/core/web/test_ops_components.py -v`
- [ ] `task qa:prepush` (or `zsh ./scripts/prepush-gate.zsh` if `task` mise shims fail)

## Debug

- ImportError on `metagit.core.component.detect` usually means the module is missing or imported via package `__init__`.
- Empty candidates with a real monorepo: confirm the scan root is the repo checkout (`definition_root / repo.path`), not the umbrella manifest directory.
- Apply wrote nothing: path already catalogued, `validate_components` rejected the add, or `--apply` was omitted.

## Update Scaffold

- [ ] `.mex/ROUTER.md` project state
- [ ] `docs/concepts/components.md` operator CLI
- [ ] modality `component_detect`
