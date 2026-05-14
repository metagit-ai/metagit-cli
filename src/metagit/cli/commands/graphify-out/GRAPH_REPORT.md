# Graph Report - .  (2026-05-11)

## Corpus Check
- Corpus is ~7,731 words - fits in a single context window. You may not need a graph.

## Summary
- 132 nodes · 149 edges · 12 communities (11 shown, 1 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Record Commands|Record Commands]]
- [[_COMMUNITY_Config Commands|Config Commands]]
- [[_COMMUNITY_App Config Commands|App Config Commands]]
- [[_COMMUNITY_Git Cache Commands|Git Cache Commands]]
- [[_COMMUNITY_Repo Setup Flow|Repo Setup Flow]]
- [[_COMMUNITY_MCP And Repo Add|MCP And Repo Add]]
- [[_COMMUNITY_Detection Commands|Detection Commands]]
- [[_COMMUNITY_Skills Commands|Skills Commands]]
- [[_COMMUNITY_Project Commands|Project Commands]]
- [[_COMMUNITY_Project Source Sync|Project Source Sync]]
- [[_COMMUNITY_Workspace Commands|Workspace Commands]]
- [[_COMMUNITY_JSON Time Encoding|JSON Time Encoding]]

## God Nodes (most connected - your core abstractions)
1. `path()` - 16 edges
2. `_get_record_manager()` - 11 edges
3. `list()` - 6 edges
4. `init()` - 5 edges
5. `_update_gitignore()` - 5 edges
6. `record_create()` - 4 edges
7. `record_update()` - 4 edges
8. `record_export()` - 4 edges
9. `record_import()` - 4 edges
10. `repo()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `skills_install()` --calls--> `list()`  [INFERRED]
  skills.py → gitcache.py
- `init()` --calls--> `path()`  [INFERRED]
  init.py → gitcache.py
- `_update_gitignore()` --calls--> `path()`  [INFERRED]
  init.py → gitcache.py
- `init()` --calls--> `repo()`  [INFERRED]
  init.py → project_repo.py
- `repo_add()` --calls--> `list()`  [INFERRED]
  project_repo.py → gitcache.py

## Communities (12 total, 1 thin omitted)

### Community 0 - "Record Commands"
Cohesion: 0.16
Nodes (19): path(), Get the path to a cached repository., _get_record_manager(), Get a configured MetagitRecordManager instance., Create a record from metagit configuration, Update an existing record, Export a record to file, Import a record from file (+11 more)

### Community 1 - "Config Commands"
Cohesion: 0.12
Nodes (16): config(), config_create(), config_info(), config_schema(), config_set(), config_show(), config_validate(), providers() (+8 more)

### Community 2 - "App Config Commands"
Cohesion: 0.12
Nodes (16): appconfig(), appconfig_create(), appconfig_get(), appconfig_info(), appconfig_schema(), appconfig_set(), appconfig_show(), appconfig_validate() (+8 more)

### Community 3 - "Git Cache Commands"
Cohesion: 0.13
Nodes (14): cache(), clear(), details(), gitcache(), Show cache statistics., Refresh a cache entry., Remove a cache entry., Git cache management commands. (+6 more)

### Community 4 - "Repo Setup Flow"
Cohesion: 0.2
Nodes (10): init(), Sanitize workspace path to ensure it is a valid path without leading ./ and with, Update .gitignore file to include workspace path., Initialize local metagit environment by creating .metagit.yml and updating .giti, _sanitize_workspace_path(), _update_gitignore(), Repository subcommands, Select project repo to work on (+2 more)

### Community 5 - "MCP And Repo Add"
Cohesion: 0.18
Nodes (10): list(), List all cache entries., install(), mcp(), Metagit MCP server commands., Start MCP runtime over stdio., Install metagit MCP server entry into supported agent configs., serve() (+2 more)

### Community 6 - "Detection Commands"
Cohesion: 0.2
Nodes (8): detect(), detect_project(), detect_repo_map(), detect_repository(), Create a map of files and folders in a repository for further analysis., Detection subcommands, Comprehensive repository analysis and MetagitConfig generation using DetectionMa, Perform project detection and analysis.

### Community 7 - "Skills Commands"
Cohesion: 0.22
Nodes (8): Bundled skill management commands., List bundled skills available for install., Show a bundled skill document., Install bundled skills into supported agent targets., skills(), skills_install(), skills_list(), skills_show()

### Community 8 - "Project Commands"
Cohesion: 0.25
Nodes (6): project_list(), project_select(), project_sync(), Shortcut: Uses 'project repo select' to select workspace project repo to work on, Sync project within workspace, List the current project configuration in YAML format

### Community 9 - "Project Source Sync"
Cohesion: 0.4
Nodes (4): Source-backed project sync operations., Discover and sync repositories from provider sources., source(), source_sync()

### Community 10 - "Workspace Commands"
Cohesion: 0.4
Nodes (4): Workspace subcommands, Select project repo to work on, workspace(), workspace_select()

## Knowledge Gaps
- **57 isolated node(s):** `Repository subcommands`, `Select project repo to work on`, `Add a repository to the current project`, `Configuration subcommands`, `Show metagit configuration` (+52 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `path()` connect `Record Commands` to `Git Cache Commands`, `Repo Setup Flow`, `MCP And Repo Add`?**
  _High betweenness centrality (0.179) - this node is a cross-community bridge._
- **Why does `list()` connect `MCP And Repo Add` to `Record Commands`, `Git Cache Commands`, `Skills Commands`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Why does `skills_install()` connect `Skills Commands` to `MCP And Repo Add`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `path()` (e.g. with `_get_record_manager()` and `record_create()`) actually correct?**
  _`path()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `list()` (e.g. with `repo_add()` and `skills_install()`) actually correct?**
  _`list()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `init()` (e.g. with `path()` and `repo()`) actually correct?**
  _`init()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Repository subcommands`, `Select project repo to work on`, `Add a repository to the current project` to the rest of the system?**
  _57 weakly-connected nodes found - possible documentation gaps or missing edges._