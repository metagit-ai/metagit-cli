schema_version: "1.0"
slug: {{ campaign_slug }}
title: Language rewrite campaign
status: draft
goal: |
  Reach behavioral parity between the source reference repository and the target
  rewrite repository.
reference_impl: rewrite/{{ source_repo_name }}
selection:
  tags: {}
repos:
  - project: rewrite
    repo: {{ source_repo_name }}
    role: reference
    status: merged
    note: Canonical reference implementation
  - project: rewrite
    repo: {{ target_repo_name }}
    role: implementation
    status: pending
    note: Bootstrap target repo and expand objectives
