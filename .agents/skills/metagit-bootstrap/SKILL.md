---
name: metagit-bootstrap
description: Create or refine a local .metagit.yml. Default is deterministic `metagit init`; do not dump detect payloads into context.
metadata:
  internal: true
---
# Metagit bootstrap

Create a valid `.metagit.yml` with **minimal tokens**. Prefer code over sampling.

## Token rules

- Default to **deterministic init**. Do not start with MCP sampling or `config example`.
- Never run `metagit detect repo_map` (full directory maps blow the context window).
- Never paste full detect YAML/JSON into the conversation. Write it to a file and read only the fields you need.
- Prefer `detect … -o summary` on stdout. Use `--output-file` for the full payload.

## Default path (deterministic)

```bash
export METAGIT_AGENT_MODE=true
# missing manifest:
metagit init --kind application --no-prompt
# or:
SKILL_ROOT="$(python3 -c "import metagit, pathlib; print(pathlib.Path(metagit.__file__).parent / 'data/skills/metagit-bootstrap')")"
"$SKILL_ROOT/scripts/bootstrap-config.sh" .
metagit config validate -c .metagit.yml
```

`bootstrap-config.sh` writes a minimal application scaffold when `.metagit.yml` is missing and prints `status=written|exists`. Do not overwrite a valid manifest without explicit confirmation.

Existing manifest: `metagit config validate -c .metagit.yml`. Patch with `metagit config patch` — do not regenerate from detect dumps.

## Optional enrichment (file-backed)

Only after init, and only if catalog fields are still empty:

```bash
mkdir -p .metagit/.detect
metagit detect repository -p . -o summary
metagit detect repository -p . -o json --output-file .metagit/.detect/repository.json
# jq '.language, .kind, .frameworks' .metagit/.detect/repository.json
```

Stdout of `--output-file` is a compact line (`status=written path=… bytes=… format=json`). Do not `cat` the file unless selecting fields.

`detect repo` / `detect project` follow the same rule: `--output-file .metagit/.detect/…` or `-o summary`. Skip them if summary already has language/kind.

## Incremental patch

```bash
metagit config show -c .metagit.yml --json
metagit config patch -c .metagit.yml --op set --path <path> --value <json> --save
metagit prompt repo -p P -n R -k repo-enrich --text-only
```

## MCP sampling (optional, not default)

Use `metagit_bootstrap_config` only when the host supports `sampling/createMessage` **and** the operator asked for a richer draft than `init`. Discovery context is already a short artifact list — do not attach repo maps. Validate YAML; write `.metagit.yml` only with `confirm_write=true`. Plan-only: return the prompt, do not invent repos.

## Safety

- Never overwrite `.metagit.yml` silently.
- Never emit secrets. Prefer placeholders for tokens.
- Do not invent repositories or unverifiable dependencies.
