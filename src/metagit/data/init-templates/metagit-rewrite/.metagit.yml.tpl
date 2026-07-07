name: {{ name }}
description: |
  {{ description }}
kind: umbrella
url: {{ url }}
agent_instructions: |
  You are the rewrite orchestrator for this workspace. The source repo is the
  specification; the target repo is the implementation. You do not invent ad-hoc
  clone paths or skip manifest validation.

  Session start (every time):
  1. `metagit context pack --tier 2 --json -c .metagit.yml`
  2. `metagit prompt workspace -k session-start --text-only -c .metagit.yml`
  3. `metagit campaign status --slug {{ campaign_slug }} --json`
  4. Read `_rewrite/parity-registry.yml` for module-level parity expectations.

  Orchestration rules:
  - Stay at workspace level for sequencing, parity gates, and MR rollups.
  - Delegate single-repo implementation to subagents with repo-scoped instructions.
  - Update campaign repo rows (`metagit campaign set`) when MRs open or merge.
  - Bind objectives to MRs: `mr_url` and `approval_id` on `context objective set`.
  - Request human approval before destructive sync, schema breaks, or parity downgrades.

workspace:
  description: |
    Rewrite workspace registry. Source and target repos share one project so
    campaigns, graph edges, and context packs treat them as a pair.
  agent_instructions: |
    Validate after manifest edits (`metagit config validate`). Commit `_campaigns/`
    and `_rewrite/` to git so rollups and parity maps stay reviewable.
  agent_profile:
    skills:
      - metagit-cli
      - metagit-context-pack
      - metagit-campaign
      - metagit-rewrite-campaign
      - metagit-multi-repo
    mcp:
      - metagit
    inherit: true
  projects:
    - name: rewrite
      description: Source (reference) and target (rewrite) repositories.
      agent_instructions: |
        Source repo agents read and analyze; target repo agents implement parity.
      repos:
        - name: {{ source_repo_name }}
          description: Reference implementation (canonical behavior and tests).
          url: {{ source_repo_url }}
          sync: true
          tags:
            role: reference
            parity: complete
          agent_instructions: |
            Read-only for rewrite agents unless fixing blockers in the reference tree.
            Use `metagit context repomix --profile rewrite-source` for scoped context.

        - name: {{ target_repo_name }}
          description: Rewrite implementation (new language or stack).
          url: {{ target_repo_url }}
          sync: true
          tags:
            role: implementation
            parity: pending
          agent_instructions: |
            Implement against the source repo and `_rewrite/parity-registry.yml`.
            Use `metagit context repomix --profile rewrite-target` for scoped context.

graph:
  relationships:
    - id: rewrite-target-implements-source
      from:
        project: rewrite
        repo: {{ target_repo_name }}
      to:
        project: rewrite
        repo: {{ source_repo_name }}
      type: implements
      label: Target reimplements source
      description: Target must reach behavioral parity with the source reference.
      tags:
        campaign: {{ campaign_slug }}
