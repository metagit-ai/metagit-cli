# Components

<!-- modality:component_model -->

A **component** is a semantic, executable, context-bearing unit of a software system. It lives **inside** a Git repository (or an application manifest’s local `paths`). It is not a second “monorepo mode.”

```text
Workspace → Project → Repository → Component
```

- **Repository** = version-control boundary (`ProjectPath`)
- **Component** = semantic/operational boundary

## Identity

Every component has a stable id:

```text
project/repo/component
```

On application manifests (no `workspace.projects[]`), both `project` and `repo` are `config.name`. Paths are not identities; they can move.

## Declaring components

### Workspace repository (native)

```yaml
workspace:
  projects:
    - name: platform
      repos:
        - name: core
          path: ./platform
          components:
            - name: web
              path: apps/web
              kind: application
              depends_on:
                - api
            - name: api
              path: apps/api
              kind: service
```

Required fields: `name`, `path` (repository-relative). Everything else is optional (`kind`, language, commands, `depends_on`, `produces`, `deploys_to`, `skills`, `tags`, `agent_instructions`, `agent_profile`).

`kind` is an open string. Recommended values: `application`, `service`, `library`, `package`, `infrastructure`, `worker`, `cli`, `plugin`, `documentation`, `data`, `tool`, `unknown`.

### Application manifests (adapter)

Existing top-level `paths[]` (and top-level `components[]` that have a local `path`) are **mapped** into the same component catalog. Those YAML lists stay `ProjectPath` objects; they are not rewritten. Top-level `components[]` that only have a `ref` remain cross-project dependency-like entries and are **not** catalog members.

A repository with no `components` key is valid and catalogs as empty.

## Validation

`metagit config validate` checks:

- duplicate names or normalized paths within a repo
- paths that escape the repository root
- unknown **same-repo** `depends_on` names and same-repo cycles
- missing component directories **when the repo checkout exists** (uncloned repos skip this)
- invalid `agent_profile` skill/MCP/rule ids on components

Nested paths (`apps/web` and `apps/web/packages/auth`) are allowed.

## Lookup and resolve

<!-- modality:component_resolve -->

```bash
metagit component list [-c .metagit.yml] [--project P] [--repo R] [--json]
metagit component show <name-or-id> [-c .metagit.yml] [--project P] [--repo R] [--json]
metagit component resolve <path> [-c .metagit.yml] [--project P] [--repo R] [--json]
```

MCP (ACTIVE workspace): `metagit_component_list`, `metagit_component_show`, `metagit_component_resolve`.

Web (read-only): `GET /v3/ops/components?project=&repo=`, `GET /v3/ops/components/resolve?path=&project=&repo=`.

`resolve` longest-matches a repo-relative or filesystem path to the most specific catalogued component. A miss is `matched: false` (not an exception). Ambiguous names or cross-repo paths are errors — pass `--project` and `--repo`, or a full `project/repo/component` id.

`--config-path/-c` is on each CLI subcommand so `component list -c FILE` works.

## Neighborhood graph

<!-- modality:component_graph -->

```bash
metagit component graph <identity> [-c .metagit.yml] [--project P] [--repo R] [--depth 1] [--direction out|in|both] [--json]
```

MCP (ACTIVE workspace): `metagit_component_graph` (required `component`; optional `project`, `repo`, `depth`, `direction`).

Web: `GET /v3/ops/components/graph?component=&project=&repo=&depth=&direction=`. Missing `component` or invalid depth/direction is 400; unknown identity is 404.

Neighborhood combines durable `graph.relationships` (`origin: declared`) with same-catalog `Component.depends_on`. Depth defaults to 1 (cap 5). Cypher export emits `kind=component` nodes for `from.component` / `to.component` endpoints, plus a `contains` edge from the parent repo when structure export is on.

## Context compile

<!-- modality:context_compile -->

```bash
metagit context compile --project P --repo R [--component NAME] [--depth N] --json
```

MCP (ACTIVE workspace): `metagit_context_compile` optional `component` and `depth` (default 0, cap 5). Unknown component and a three-segment id that disagrees with `--project`/`--repo` are errors. The compiled pack stays project/repo scoped; `component` / `component_graph` / `effective_profile` are extra sections.

## Claims

<!-- modality:acl_claim -->

Catalogued components can be claimed without a whole-repo glob. `--component` stores the component **name**; `repository` stays `project/repo`. Empty `--pattern` expands to `{path}/**` (or `**` when the component path is `.`). Explicit patterns are stored as given. Overlap is still keyed by repository + patterns, so `web` vs `api` do not conflict when their paths do not overlap.

```bash
metagit claim declare --repository platform/core --agent-id agent-1 --component web
metagit claim check --repository platform/core --component api
```

MCP (ACTIVE workspace): `metagit_claim_declare` / `metagit_claim_check` accept optional `component`. Patterns may be empty when `component` is set.

## Detect and init

<!-- modality:component_detect -->

```bash
metagit component detect [-c .metagit.yml] [--project P] [--repo R] [--apply] [--json]
metagit component init PATH [--name NAME] [--kind KIND] [--project P] [--repo R] [--apply] [--json] [-c .metagit.yml]
```

MCP (ACTIVE workspace): `metagit_component_detect` (optional `project`, `repo`, `apply`) and `metagit_component_init` (required `path`; optional `name`, `kind`, `project`, `repo`, `apply`).

Web: `GET /v3/ops/components/detect?project=&repo=` (read-only) and `POST /v3/ops/components/init` with a JSON body. Detect without `--apply` / `apply: true` never writes the manifest.

Detection is filesystem-marker only (no LLM). High-confidence markers include `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, and `*.csproj`. Kind hints follow `apps/` → application, `packages/` → package, `services/` → service, `libs/` or `internal/` → library, and `infra/` / `terraform/` / `helm/` / `charts/` → infrastructure. Nested `helm/<name>/Chart.yaml` and `charts/<name>/Chart.yaml` are also infrastructure candidates. Already catalogued paths are marked `already_catalogued`. `--apply` / `apply: true` sets `applied` only when at least one new component was written; a second init of the same path or apply on an application-kind manifest (no workspace repos) is an error, not silent success.

`init` drafts one component (name defaults to the path basename). Umbrellas need `--project` and `--repo` unless the workspace has a single repo.

## Not in this release

These land in later RFC-0026 series slices:

- derived working sets from component graphs

See the RFC-0026 Component Context Graph series under `docs/superpowers/specs/` for the remaining slices.
