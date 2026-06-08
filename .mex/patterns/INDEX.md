# Pattern Index

Lookup table for all pattern files in this directory. Check here before starting any task — if a pattern exists, follow it.

<!-- This file is populated during setup (Pass 2) and updated whenever patterns are added.
     Each row maps a pattern file (or section) to its trigger — when should the agent load it?

     Format — simple (one task per file):
     | [filename.md](filename.md) | One-line description of when to use this pattern |

     Format — anchored (multi-section file, one row per task):
     | [filename.md#task-first-task](filename.md#task-first-task) | When doing the first task |
     | [filename.md#task-second-task](filename.md#task-second-task) | When doing the second task |

     Example (from a Flask API project):
     | [add-api-client.md](add-api-client.md) | Adding a new external service integration |
     | [debug-pipeline.md](debug-pipeline.md) | Diagnosing failures in the request pipeline |
     | [crud-operations.md#task-add-endpoint](crud-operations.md#task-add-endpoint) | Adding a new API route with validation |
     | [crud-operations.md#task-add-model](crud-operations.md#task-add-model) | Adding a new database model |

     Keep this table sorted alphabetically. One row per task (not per file).
     If you create a new pattern, add it here. If you delete one, remove it. -->

| Pattern | Use when |
|---------|----------|
| [add-cli-command.md](add-cli-command.md) | Adding or extending a Click CLI command while keeping core logic in `src/metagit/core/*` |
| [add-prompt-catalog-kind.md](add-prompt-catalog-kind.md) | Adding a new built-in `metagit prompt` kind (catalog + template + tests) |
| [add-managed-repo-search.md](add-managed-repo-search.md) | Extending or debugging managed-only repo search (CLI, MCP `metagit_repo_search`, local JSON API) |
| [add-mcp-tool.md](add-mcp-tool.md) | Adding/changing MCP tools, schemas, dispatch behavior, and runtime tests |
| [mcp-project-context.md](mcp-project-context.md) | Project context switch, session store, or workspace snapshot MCP tools |
| [mcp-cross-project-dependencies.md](mcp-cross-project-dependencies.md) | Cross-project dependency graph MCP tool and collectors |
| [metagit-web-api.md](metagit-web-api.md) | Adding or changing Pydantic models and routes for `metagit web serve` |
| [bootstrap-metagit-config.md](bootstrap-metagit-config.md) | Creating, validating, or repairing `.metagit.yml` for workspace and MCP flows |
| [changelog-release.md](changelog-release.md) | Updating `CHANGELOG.md`, docs publishing, and semantic-release note promotion |
| [context-pack-repo-cards.md](context-pack-repo-cards.md) | Tier-1 context pack repo cards (`RepoCardService`, index + `inspect_repo_state`) |
| [optimize-agent-access.md](optimize-agent-access.md) | Scaffold llms.txt, AGENTS.md, hidden README agent HTML via `metagit-agent-access` skill |
| [debug-mcp-runtime.md](debug-mcp-runtime.md) | Diagnosing MCP runtime protocol, framing, gating, and tool/resource failures |
| [debug-workspace-discovery.md](debug-workspace-discovery.md) | Diagnosing empty/incorrect workspace index, search hits, or upstream hint ranking |
| [project-cli-resolution.md](project-cli-resolution.md) | Fixing or extending `metagit project list/select` when app-config default ≠ manifest projects |
| [repo-promote-local-to-git.md](repo-promote-local-to-git.md) | Migrating a path-based workspace repo entry to a git-managed clone (`project repo promote`) |
| [github-gh-auth.md](github-gh-auth.md) | Creating PRs or running `gh` when `GH_TOKEN`/`GITHUB_TOKEN` cause 401 errors |
| [run-graphify-analysis.md](run-graphify-analysis.md) | Running `graphify` on the repo or a focused subtree and turning the result into usable graph/report outputs |
| [update-release-workflow.md](update-release-workflow.md) | Replacing or repairing GitHub release automation and tag-driven publish flow |
| [validate-doc-links.md](validate-doc-links.md) | Adding or fixing links in README.md and docs/**/*.md; run `task docs:links` |
