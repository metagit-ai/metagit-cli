# CI Targets

Durable CI topology bindings for managed workspace repositories (`ProjectPath.ci`).

Orchestrators use this to answer **where CI/CD lives** for a repo without polling live pipeline APIs.

## Shape

Optional `ci` on each `workspace.projects[].repos[]` entry:

```yaml
ci:
  provider: azure_devops   # github | gitlab | azure_devops | other | none | unknown
  config_paths:
    - azure-pipelines.yml
  host: dev.azure.com
  organization: contoso
  project: PaySystem
  repository: payments-api
  definition_ids: []       # optional ADO overrides
  status: detected         # detected | declared | overridden
  updated_at: "2026-08-20T12:00:00Z"
```

- `detected` — filled by remote URL + on-disk CI file scan
- `declared` / `overridden` — human or agent edits; re-detect will not clobber without `--force`

## Commands

```bash
metagit -p PROJECT project repo ci show --repo REPO --json
metagit -p PROJECT project repo ci detect --repo REPO [--apply] [--force] --json
metagit -p PROJECT project repo ci set --repo REPO --provider azure_devops \
  --organization ORG --ado-project PROJECT --repository REPO_NAME --json
```

## MCP

- `metagit_repo_ci_show`
- `metagit_repo_ci_detect` (`apply`, `force` optional)

Tier-1 repo cards include a compact `ci` summary when present.

## Azure DevOps source import

```bash
metagit project -p PROJECT source sync \
  --provider azure_devops \
  --organization contoso \
  [--ado-project PaySystem] \
  --mode additive --ensure --apply --json
```

App config:

```yaml
providers:
  azure_devops:
    enabled: true
    api_token: "${METAGIT_AZURE_DEVOPS_API_TOKEN}"
    base_url: https://dev.azure.com
```

Env: `METAGIT_AZURE_DEVOPS_ENABLED`, `METAGIT_AZURE_DEVOPS_API_TOKEN` (or `AZURE_DEVOPS_EXT_PAT`), `METAGIT_AZURE_DEVOPS_BASE_URL`.

## Live pipelines (deferred)

Web CI/CD live status for ADO is Phase 2 and will consume `ProjectPath.ci` locators before falling back to remote URL parsing.

Design: [docs/superpowers/specs/2026-08-20-azure-devops-ci-topology-design.md](../superpowers/specs/2026-08-20-azure-devops-ci-topology-design.md)
