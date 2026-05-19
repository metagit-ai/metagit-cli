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
