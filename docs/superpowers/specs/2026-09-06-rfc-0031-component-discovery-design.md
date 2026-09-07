# RFC-0031: Component Discovery + Init — Design

**Status:** Implemented
**Date:** 2026-09-06
**Series:** [Component Context Graph index](2026-09-06-rfc-0026-component-context-graph-index.md)
**Depends on:** [RFC-0027](2026-09-06-rfc-0027-component-resolution-design.md)
**Plan:** [2026-09-06-rfc-0028-0032-remaining-series.md](../plans/2026-09-06-rfc-0028-0032-remaining-series.md)

## Summary

Detect candidate components from filesystem markers and optionally write them into `repos[].components[]`. Init creates one declarative component at a path. Detection never silently mutates the manifest without `--apply`.

## Goals

- `metagit component detect` → candidates with kind, language hints, confidence.
- `metagit component init <path>` → one draft; `--apply` writes YAML.
- Skip paths already in the catalog.
- No LLM.

## Non-Goals

- Rewriting application `paths[]` types
- Auto-creating a whole-repo component when none exist unless `init .`
- Deep language version parsing beyond marker files
- SPA detect UI (API only)

## Decisions (locked)

1. **Service:** `ComponentDetector` in `src/metagit/core/component/detect.py`. Do not import from package `__init__`.
2. **Scan root** is the resolved repo checkout (`definition_root / repo.path` for workspace; `definition_root` for application).
3. **Candidate directories** (first existing wins, not nested under another candidate except documented nested packages):
   - Immediate children of `apps/`, `packages/`, `services/`, `libs/`, `internal/` that contain a marker.
   - `infra/`, `terraform/`, `helm/`, `charts/` as `infrastructure` when they contain `.tf`, `Chart.yaml`, or `helmfile.yaml`.
4. **Markers (high confidence):** `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `*.csproj`, `uv.lock` sibling to `pyproject.toml`.
5. **Medium confidence:** directory name matches convention (`apps/foo`) with a `Dockerfile` or `Taskfile.yml` / `Makefile` only.
6. **Skip:** `.git`, `node_modules`, `dist`, `build`, `.venv`, `__pycache__`, `.tox`, `vendor`, catalogued paths, nested marker dirs under an already-chosen candidate (do not emit `apps/web/src`).
7. **Name** is the directory basename, POSIX-normalized. Invalid names (empty, contain `/`) are skipped.
8. **`--apply`** appends `Component(name, path, kind, language?)` to the matching workspace repo’s `components[]` and saves via `MetagitConfigManager`. Existing names/paths that would fail `validate_components` are reported and skipped (no partial corrupt write: collect valid adds, then save once).
9. **`init <path>`** requires `--project` and `--repo` on umbrellas (or unique mapping). Name defaults to basename. `--apply` writes one component.
10. **Detect without `--apply`** is read-only.
11. **MCP:** `metagit_component_detect` (optional `project`, `repo`, `apply`) and `metagit_component_init` (required `path`; optional `name`, `kind`, `project`, `repo`, `apply`). `apply: true` is a mutation; keep ACTIVE-state gating same as other manifest writes if a write tool exists — if claim/config patch tools are ACTIVE, detect apply is ACTIVE too.
12. **Web:** `GET /v3/ops/components/detect` (register before `/components`). `POST /v3/ops/components/init` with JSON body. Detect GET is read-only; POST init with `apply` writes.
13. **Modality id** `component_detect`.

## Candidate JSON

```json
{
  "candidates": [
    {
      "name": "web",
      "path": "apps/web",
      "kind": "application",
      "language": "typescript",
      "confidence": "high",
      "markers": ["package.json"],
      "already_catalogued": false
    }
  ]
}
```

## Tests

- Fixture tree with `apps/web/package.json` + `apps/api/pyproject.toml` yields two high candidates.
- Nested `apps/web/src/package.json` is not a candidate if `apps/web` already is.
- Catalogued `apps/web` is marked `already_catalogued` and omitted from `--apply`.
- `init apps/web --apply` writes `components[]`.
- No-marker empty repo → empty candidates, exit 0.
