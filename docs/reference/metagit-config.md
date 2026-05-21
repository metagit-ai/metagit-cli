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

- [schemas/metagit_config.schema.json](../../schemas/metagit_config.schema.json)
- [schemas/metagit_appconfig.schema.json](../../schemas/metagit_appconfig.schema.json)

## Validate your manifest

```bash
metagit config validate --config-path .metagit.yml
```

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
