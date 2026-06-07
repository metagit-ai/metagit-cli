# Metagit configuration exemplar

The file [metagit-config.full-example.yml](metagit-config.full-example.yml) is a **generated,
non-production** sample of `.metagit.yml` with representative values and Pydantic field
descriptions as comments.

## Regenerate

From the repository root:

```bash
task generate:schema
```

That runs `metagit config schema`, `metagit appconfig schema`, and `metagit config example`.

To emit only the YAML exemplar:

```bash
metagit config example --output docs/reference/metagit-config.full-example.yml
```

Overrides merged from `src/metagit/data/config-example-overrides.yml` keep the workspace and
Hermes-oriented examples readable.

## Machine-readable schema

JSON Schema for editors and CI:

- [metagit_config.schema.json](schemas/metagit_config.schema.json)
- [metagit_appconfig.schema.json](schemas/metagit_appconfig.schema.json)

## Validate your manifest

```bash
metagit config validate --config-path .metagit.yml
```

## Schema-backed editing (CLI)

The same operation model as the web Config Studio is available on the CLI:

| Command | Purpose |
|---------|---------|
| `metagit config tree` | Browse fields, types, and paths |
| `metagit config preview` | Apply draft ops and print YAML (no save) |
| `metagit config patch --save` | Apply ops and write `.metagit.yml` when valid |
| `metagit appconfig tree` | App config field tree |
| `metagit appconfig preview` | Draft preview (secrets redacted) |
| `metagit appconfig patch --save` | Apply ops to `metagit.config.yaml` |

Operations: `enable`, `disable`, `set`, `append`, `remove`. Paths use dot/bracket notation
(e.g. `workspace.projects[0].name`, `documentation[0].path`).

```bash
# Single field
metagit config patch --op set --path name --value my-workspace --save

# Batch from JSON (same shape as web PATCH body)
metagit config patch --file ops.json --save
```

`ops.json` may be `{"operations": [...]}` or a bare array of operation objects.

Do not deploy the generated exemplar verbatim; copy sections you need and replace placeholders.

## Documentation sources

The top-level `documentation` list accepts **bare strings** or **objects**:

- A string without `http(s)://` is treated as `kind: markdown` with `path` set to that string.
- A URL string becomes `kind: web`.
- Objects support `kind`, `path`, `url`, `title`, `description`, `tags` (list or map), and `metadata` (map) for knowledge-graph ingestion.

Use `MetagitConfig.documentation_graph_nodes()` (or export from your tooling) to emit normalized node payloads.

## Manual graph relationships

The optional top-level `graph` block declares cross-repo edges that are not inferred from imports or URLs:

```yaml
graph:
  metadata:
    source: manual
  relationships:
    - id: platform-api-uses-infra-tf
      from:
        project: platform
        repo: api
      to:
        project: infra
        repo: terraform-modules
      type: depends_on
      label: API stack depends on shared modules
      tags:
        layer: platform
```

These edges are merged into cross-project dependency maps (`type: manual`) and available via `MetagitConfig.graph_export_payload()` for GitNexus-style exports. Request dependency type `manual` when calling `metagit_cross_project_dependencies` to focus on manifest-declared edges.

### Discover and suggest relationships (agent automation)

**First-time / empty graph** — guided discovery report (no auto-apply):

```bash
metagit prompt workspace -c .metagit.yml -k graph-discover --text-only
metagit config graph suggest -c .metagit.yml --json --include-declared --min-confidence all
```

Promote inferred cross-project edges into durable `graph.relationships` entries:

```bash
metagit config graph suggest -c .metagit.yml --json
metagit config graph suggest -c .metagit.yml --min-confidence high --apply
metagit prompt workspace -c .metagit.yml -k graph-maintain --text-only
```

MCP: `metagit_suggest_graph_relationships`, `metagit_apply_graph_relationships`. Bundled skill: `metagit-graph-maintain`.

### Export to GitNexus (Cypher)

Export manual relationships (and optional structure/documentation nodes) as Cypher for `gitnexus_cypher` MCP tool calls:

```bash
metagit config graph export -c .metagit.yml --format json
metagit config graph export -c .metagit.yml --format cypher --output workspace-graph.cypher
metagit config graph export -c .metagit.yml --format tool-calls --manual-only
./skills/metagit-gitnexus/scripts/ingest-workspace-graph.sh -c .metagit.yml
```

The exporter creates overlay tables `MetagitEntity` and `MetagitLink` (run `schema_statements` once per target GitNexus index), then `MERGE`/`CREATE` workspace nodes and manual edges. MCP: `metagit_export_workspace_graph_cypher`.

Pass `--gitnexus-repo <name>` when the umbrella workspace is indexed under a different GitNexus repo name than the manifest `name` field.

### GitNexus group sync (cross-index)

Register all managed workspace repos in a GitNexus group for `group query`, `group impact`, and contract linking:

```bash
metagit gitnexus group sync -c .metagit.yml --json
metagit gitnexus group sync -c .metagit.yml --group-name my-workspace --prune
./skills/metagit-gitnexus/scripts/sync-group.sh -c .metagit.yml
```

MCP: `metagit_gitnexus_group_sync`. Requires each checkout to be analyzed (`gitnexus analyze`) and present in `~/.gitnexus/registry.json`. Group member paths use `<project>/<repo>`.
