---
name: metagit-config-refresh
description: Refresh or bootstrap `.metagit.yml` using deterministic init/validate. Use when configuration is missing, stale, or incomplete for workspace operations.
---

# Refreshing Project Config

Keep `.metagit.yml` accurate without dumping detect output into context.

## Workflow

1. `metagit config validate -c .metagit.yml` (or note that the file is missing).
2. If missing: `metagit init --kind application --no-prompt` or `skills/metagit-bootstrap/scripts/bootstrap-config.sh .`
3. Optional enrich: `metagit detect repository -p . -o summary`, or `--output-file .metagit/.detect/repository.json` for the full payload. Do not run `detect repo_map`.
4. Patch with `metagit config patch` / catalog commands. Re-validate.

## Output contract

Return config health before/after, a short update summary, and any manual follow-up. Do not paste full YAML.

## Safety

- Prefer plan/dry-run for large updates.
- Never overwrite a valid umbrella workspace mapping without confirmation.
