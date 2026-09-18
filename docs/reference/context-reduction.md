# Large-workspace context reduction and board-linked campaigns

<!-- modality:context_reduction -->
<!-- modality:campaign_board_link -->

Umbrella manifests stay on disk. Agents receive **summaries, pages, and search hits**.

## Caps (defaults)

| Surface | Default page | Opt-in full dump |
|---------|--------------|------------------|
| Workspace map / pack map | 80 repos | `--max-map-repos` / `?limit=` / `limit: 0` on list |
| `workspace list` `repos_index` | 80 | `--limit 0` |
| `workspace repo list` | 80 slim rows | `--detail full` (single-project) + `--limit 0` |
| Session digest rows | 40 | scoped `--project`/`--repo` |
| Campaign status / expand / board-sync | 40 | `--offset` pages |
| Full `.metagit.yml` JSON | refused above 80 repos | `--confirm-full` / `?view=full&confirm=1` |

`workspace list` **does not** embed `summary.workspace` unless `--include-workspace`.

## Agent commands

```bash
export METAGIT_AGENT_MODE=true
metagit context pack --tier 0 --json --project platform
metagit search "payments" --json --limit 10
metagit campaign new --slug payments-rollout --title "Payments rollout" --query "payments" --json
metagit campaign status --slug payments-rollout --json --limit 40
metagit campaign expand --slug payments-rollout --limit 40 --offset 0 --json
metagit campaign board-sync --slug payments-rollout \
  --organization myorg --ado-project platform --dry-run --json
```

Prompt: `metagit prompt workspace -k large-workspace --text-only`.

## MCP

| Need | Tool / resource |
|------|-----------------|
| Paged map | `metagit://workspace/map?limit=80` or `metagit_context_pack` |
| Catalog | `metagit_workspace_list` (`include_workspace` default false) |
| Slim repos | `metagit_workspace_repos_list` `detail: slim` |
| Campaign page | `metagit_campaign_status` |
| ADO WIT | `metagit_campaign_board_sync` (`dry_run: true` first) |
| Full manifest | refused unless `?view=full&confirm=1` |

HTTP: `GET /v2/workspace?limit=80`, `GET /v2/repos?detail=slim&limit=80`.

See [campaigns.md](campaigns.md) for board fields and [mcp-layered-resources-spec.md](mcp-layered-resources-spec.md) for the resource ladder.
