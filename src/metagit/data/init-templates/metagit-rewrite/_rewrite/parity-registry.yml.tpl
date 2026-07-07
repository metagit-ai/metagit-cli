# Module-level parity registry (BYO convention — not validated by metagit schema).
schema_version: "1.0"
campaign_slug: {{ campaign_slug }}
source:
  project: rewrite
  repo: {{ source_repo_name }}
target:
  project: rewrite
  repo: {{ target_repo_name }}
phases:
  - id: foundation
    title: Core models and config
    modules:
      - id: config-manager
        title: Config load/save/validate
        source_path: src/
        target_path: src/
        status: pending
  - id: cli-surface
    title: CLI command surface
    modules:
      - id: cli-core
        title: Primary CLI groups
        source_path: src/
        target_path: src/
        status: pending
