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

## Not in this release

These land in later RFC-0026 series slices:

- `metagit component list|show|resolve|detect|init|graph`
- `context compile --component`
- graph `from.component` / `to.component`
- component-level claims/ownership
- derived working sets from component graphs
- MCP component tools

See the RFC-0026 Component Context Graph series under `docs/superpowers/specs/` for the remaining slices.
