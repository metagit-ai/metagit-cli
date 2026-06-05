#!/usr/bin/env python3
"""Scaffold bundled agent template directories for the catalog."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_ROOT = ROOT / "src/metagit/data/agent-templates"
OVERSEER = TEMPLATES_ROOT / "orchestration-overseer"

VENDOR_BLOCK = """  claude_code:
    filename: {id}.md
  cursor:
    filename: {id}.md
    template: {id}.cursor.md.tpl
  github_copilot:
    filename: {id}.agent.md
    template: {id}.github-copilot.agent.md.tpl
  hermes:
    filename: {id}
    install_as: skill
    template: {id}.skill.md.tpl
  openclaw:
    filename: {id}
    install_as: skill
    template: {id}.skill.md.tpl
  opencode:
    filename: {id}.md
    template: {id}.opencode.md.tpl
  windsurf:
    filename: {id}
    install_as: skill
    template: {id}.skill.md.tpl
  codex:
    filename: {id}
    install_as: skill
    template: {id}.skill.md.tpl
"""

FILE_BLOCK = """files:
  - template: {id}.md.tpl
    output: {id}.md
  - template: AGENTS.md.fragment.tpl
    output: AGENTS.md.fragment
    optional: true
  - template: manifest.json.tpl
    output: manifest.json
"""

PROMPTS_BLOCK = """prompts:
  - name: workspace_name
    label: Workspace / manifest name
    default_from: directory_name
  - name: manifest_path
    label: Path to .metagit.yml (relative to coordinator root)
    default: .metagit.yml
  - name: coordinator_description
    label: Short coordinator role description
    default: Umbrella orchestrator for managed workspace projects.
"""

SPECS: list[dict[str, object]] = [
    {
        "id": "repo-implementer",
        "label": "Repo implementer",
        "description": (
            "Single-repo implementation specialist dispatched by the orchestration "
            "overseer. Focuses on scoped code changes, guarded sync, and handoff prompts."
        ),
        "archetype": "specialist",
        "scope": "repo",
        "sort_order": 20,
        "category": "Execution",
        "prompt_kinds": ["subagent-handoff", "sync-safe", "context-pack"],
        "mcp_tools": ["metagit_project_context_switch", "metagit_workspace_search"],
        "delegates_to": ["agent-access-optimizer"],
        "delegated_by": ["orchestration-overseer"],
        "recommended_skills": [
            "metagit-cli",
            "metagit-workspace-sync",
            "metagit-repo-impact",
        ],
        "tools": "Read, Write, Edit, Bash, Grep, Glob, Skill",
        "role_heading": "Repo implementer",
        "role_summary": (
            "You implement changes in **one repo** at a time under manifest-scoped "
            "instructions. Escalate cross-repo work to the orchestration overseer."
        ),
        "sections": [
            "## Non-negotiables",
            "",
            "1. Follow repo-scoped `agent_instructions` from the manifest.",
            "2. Run `metagit prompt workspace -k subagent-handoff --text-only`.",
            "3. Stay inside the assigned project/repo unless explicitly expanded.",
            "",
            '{{ include "guarded-sync" }}',
            "",
            '{{ include "manifest-validate" }}',
            "",
            '{{ include "cli-fallback" }}',
            "",
            '{{ include "output-format-health-scope" }}',
        ],
    },
    {
        "id": "graph-curator",
        "label": "Graph curator",
        "description": (
            "Maintains cross-repository graph relationships, GitNexus ingest, and "
            "group sync for workspace-wide code intelligence."
        ),
        "archetype": "specialist",
        "scope": "workspace",
        "sort_order": 30,
        "category": "Graph",
        "prompt_kinds": ["graph-discover", "graph-maintain"],
        "mcp_tools": [
            "metagit_suggest_graph_relationships",
            "metagit_apply_graph_relationships",
            "metagit_gitnexus_group_sync",
        ],
        "delegates_to": [],
        "delegated_by": ["orchestration-overseer"],
        "recommended_skills": [
            "metagit-graph-maintain",
            "metagit-gitnexus",
            "metagit-repo-impact",
        ],
        "tools": "Read, Bash, Grep, Glob, Skill",
        "role_heading": "Graph curator",
        "role_summary": (
            "You maintain durable `graph.relationships` and GitNexus overlays. "
            "Report before apply on discovery workflows."
        ),
        "sections": [
            "## Graph discovery (report only)",
            "",
            "```bash",
            "metagit prompt workspace -k graph-discover --text-only -c {{ manifest_path }}",
            "metagit config graph suggest --json -c {{ manifest_path }}",
            "```",
            "",
            "## Graph maintenance (when approved)",
            "",
            "```bash",
            "metagit prompt workspace -k graph-maintain --text-only -c {{ manifest_path }}",
            "metagit config graph suggest --apply -c {{ manifest_path }}",
            "skills/metagit-gitnexus/scripts/ingest-workspace-graph.sh .",
            "metagit gitnexus group sync -c {{ manifest_path }}",
            "```",
            "",
            '{{ include "manifest-validate" }}',
            "",
            '{{ include "cli-fallback" }}',
        ],
    },
    {
        "id": "repo-enricher",
        "label": "Repo enricher",
        "description": (
            "Enriches a single repo catalog entry via detect/source sync and "
            "repo-enrich prompt workflows."
        ),
        "archetype": "specialist",
        "scope": "repo",
        "sort_order": 60,
        "category": "Catalog",
        "prompt_kinds": ["repo-enrich"],
        "mcp_tools": ["metagit_workspace_search"],
        "delegates_to": [],
        "delegated_by": ["catalog-bootstrapper"],
        "recommended_skills": ["metagit-config-refresh", "metagit-cli"],
        "tools": "Read, Write, Bash, Grep, Glob, Skill",
        "role_heading": "Repo enricher",
        "role_summary": (
            "You enrich one repo's manifest entry with discovered metadata. "
            "Validate before claiming the catalog is updated."
        ),
        "sections": [
            "## Repo enrichment workflow",
            "",
            "1. `metagit prompt workspace -k repo-enrich --text-only -c {{ manifest_path }}`",
            "2. Detect on-disk signals (dependencies, docs, CI) for the target repo.",
            "3. Merge into the repo's `repos[]` entry and validate.",
            "",
            '{{ include "manifest-validate" }}',
            "",
            '{{ include "cli-fallback" }}',
        ],
    },
    {
        "id": "agent-access-optimizer",
        "label": "Agent access optimizer",
        "description": (
            "Optimizes agent onboarding artifacts (llms.txt, AGENTS.md) for one repo."
        ),
        "archetype": "specialist",
        "scope": "repo",
        "sort_order": 90,
        "category": "Catalog",
        "prompt_kinds": ["repo-enrich"],
        "mcp_tools": [],
        "delegates_to": [],
        "delegated_by": ["repo-implementer"],
        "recommended_skills": ["metagit-agent-access"],
        "tools": "Read, Write, Edit, Grep, Glob, Skill",
        "role_heading": "Agent access optimizer",
        "role_summary": (
            "You improve agent-readable docs for a single repo without changing runtime code."
        ),
        "sections": [
            "## Agent access workflow",
            "",
            "1. Load **metagit-agent-access** skill for the target repo.",
            "2. Audit llms.txt, AGENTS.md, and hidden agent blocks.",
            "3. Propose minimal-token onboarding improvements.",
            "",
            '{{ include "manifest-validate" }}',
        ],
    },
    {
        "id": "catalog-bootstrapper",
        "label": "Catalog bootstrapper",
        "description": (
            "Registers projects and repos in the workspace manifest using search-before-create."
        ),
        "archetype": "specialist",
        "scope": "workspace",
        "sort_order": 40,
        "category": "Workspace ops",
        "prompt_kinds": ["catalog-edit", "session-start"],
        "mcp_tools": ["metagit_workspace_search"],
        "delegates_to": ["repo-enricher"],
        "delegated_by": ["orchestration-overseer"],
        "recommended_skills": [
            "metagit-projects",
            "metagit-bootstrap",
            "metagit-config-refresh",
            "metagit-cli",
        ],
        "tools": "Read, Write, Bash, Grep, Glob, Skill",
        "role_heading": "Catalog bootstrapper",
        "role_summary": (
            "You expand the workspace catalog safely — search before create, validate after edits."
        ),
        "sections": [
            "## Catalog workflow",
            "",
            "1. `metagit prompt workspace -k catalog-edit --text-only -c {{ manifest_path }}`",
            "2. Search existing projects/repos before adding entries.",
            "3. Delegate per-repo enrichment to **repo-enricher** when metadata is thin.",
            "",
            '{{ include "session-start-checklist" }}',
            "",
            '{{ include "manifest-validate" }}',
            "",
            '{{ include "cli-fallback" }}',
        ],
    },
    {
        "id": "upstream-triage",
        "label": "Upstream triage",
        "description": (
            "Triages cross-repo blockers by ranking likely upstream repositories and files."
        ),
        "archetype": "specialist",
        "scope": "workspace",
        "sort_order": 50,
        "category": "Workspace ops",
        "prompt_kinds": ["health-preflight", "sync-safe"],
        "mcp_tools": ["metagit_workspace_search", "metagit_workspace_grep"],
        "delegates_to": [],
        "delegated_by": ["orchestration-overseer"],
        "recommended_skills": [
            "metagit-upstream-scan",
            "metagit-upstream-triage",
            "metagit-multi-repo",
        ],
        "tools": "Read, Bash, Grep, Glob, Skill",
        "role_heading": "Upstream triage",
        "role_summary": (
            "You find upstream causes when local fixes look incomplete across the workspace."
        ),
        "sections": [
            "## Triage workflow",
            "",
            "1. `metagit prompt workspace -k health-preflight --text-only -c {{ manifest_path }}`",
            "2. Use upstream-scan and upstream-triage skills to rank candidate repos.",
            "3. `metagit workspace grep` for cross-repo signal confirmation.",
            "",
            '{{ include "guarded-sync" }}',
            "",
            '{{ include "cli-fallback" }}',
            "",
            '{{ include "output-format-health-scope" }}',
        ],
    },
    {
        "id": "release-auditor",
        "label": "Release auditor",
        "description": (
            "Runs release-audit workflows, objectives tracking, and prepush gate checks."
        ),
        "archetype": "specialist",
        "scope": "workspace",
        "sort_order": 70,
        "category": "Quality",
        "prompt_kinds": ["health-preflight", "sync-safe"],
        "mcp_tools": ["metagit_workspace_health_check"],
        "delegates_to": [],
        "delegated_by": ["orchestration-overseer"],
        "recommended_skills": ["metagit-release-audit", "metagit-control-center"],
        "tools": "Read, Bash, Grep, Glob, Skill",
        "role_heading": "Release auditor",
        "role_summary": (
            "You verify release readiness across managed repos without bypassing QA gates."
        ),
        "sections": [
            "## Release audit workflow",
            "",
            "1. Load **metagit-release-audit** skill and run `task qa:prepush` where applicable.",
            "2. Check active objectives and approvals before hand-off.",
            "3. Run `task gitnexus:analyze` after code changes when graphs are in scope.",
            "",
            '{{ include "guarded-sync" }}',
            "",
            '{{ include "output-format-health-scope" }}',
        ],
    },
    {
        "id": "secret-bootstrapper",
        "label": "Secret bootstrapper",
        "description": (
            "Guides SecretZero bootstrap when Secretfile.yml is present. Never handles secret values."
        ),
        "archetype": "specialist",
        "scope": "workspace",
        "sort_order": 80,
        "category": "Security",
        "prompt_kinds": ["session-start"],
        "mcp_tools": [],
        "delegates_to": [],
        "delegated_by": ["orchestration-overseer"],
        "recommended_skills": [],
        "external_skills": [
            {
                "name": "secretzero",
                "note": "Install when any managed repo contains Secretfile.yml.",
            }
        ],
        "tools": "Read, Bash, Grep, Glob, Skill",
        "role_heading": "Secret bootstrapper",
        "role_summary": (
            "You guide operators through SecretZero bootstrap without pasting secrets into chat."
        ),
        "sections": [
            "## SecretZero workflow",
            "",
            "1. Detect `Secretfile.yml` under managed repos.",
            "2. Load **secretzero** skill and SecretZero MCP when configured.",
            "3. Never paste secrets into chat or commit them to git.",
            "4. Record non-secret outcomes via `metagit_session_update` only.",
            "",
            '{{ include "session-start-checklist" }}',
        ],
    },
    {
        "id": "iac-coordinator",
        "label": "IaC coordinator",
        "description": (
            "Control-plane agent for platform/IaC documentation, multi-repo coordination, "
            "and infrastructure project focus."
        ),
        "archetype": "control_plane",
        "scope": "workspace",
        "sort_order": 15,
        "category": "Control plane",
        "prompt_kinds": ["session-start", "catalog-edit", "sync-safe"],
        "mcp_tools": [
            "metagit_project_context_switch",
            "metagit_workspace_health_check",
            "metagit_gitnexus_group_sync",
        ],
        "delegates_to": ["repo-implementer", "graph-curator", "catalog-bootstrapper"],
        "delegated_by": ["orchestration-overseer"],
        "recommended_skills": [
            "metagit-control-center",
            "metagit-multi-repo",
            "metagit-gitnexus",
            "metagit-cli",
        ],
        "tools": "Read, Write, Edit, Bash, Grep, Glob, Agent, Skill",
        "role_heading": "IaC coordinator",
        "role_summary": (
            "You coordinate infrastructure and platform projects across the workspace, "
            "emphasizing IaC docs and cross-repo platform dependencies."
        ),
        "sections": [
            "## Platform / IaC focus",
            "",
            "1. Prioritize platform, infra, and shared-services projects in the manifest.",
            "2. Cross-check documentation links and IaC repo cards before changes.",
            "3. Delegate repo-scoped implementation to **repo-implementer**.",
            "",
            '{{ include "session-start-checklist" }}',
            "",
            '{{ include "guarded-sync" }}',
            "",
            '{{ include "manifest-validate" }}',
            "",
            '{{ include "cli-fallback" }}',
            "",
            '{{ include "output-format-health-scope" }}',
        ],
    },
]


def _skills_yaml(skills: list[str]) -> str:
    if not skills:
        return ""
    lines = ["skills:"]
    lines.extend(f"  - {skill}" for skill in skills)
    return "\n".join(lines) + "\n"


def _external_yaml(items: list[dict[str, str]]) -> str:
    if not items:
        return ""
    lines = ["external_skills:"]
    for item in items:
        lines.append(f"  - name: {item['name']}")
        lines.append(f"    note: {item['note']}")
    return "\n".join(lines) + "\n"


def _body(spec: dict[str, object]) -> str:
    heading = str(spec["role_heading"])
    summary = str(spec["role_summary"])
    sections = "\n".join(str(line) for line in spec["sections"])  # type: ignore[index]
    return (
        f"# {heading} — {{{{ workspace_name }}}}\n\n"
        f"{summary}\n\n"
        f"Manifest path: `{{{{ manifest_path }}}}`\n\n"
        f"{sections}\n"
    )


def _frontmatter(spec: dict[str, object], *, skill: bool = False) -> str:
    template_id = str(spec["id"])
    description = str(spec["description"]).strip().replace("\n", " ")
    skills = spec["recommended_skills"]  # type: ignore[assignment]
    tools = str(spec["tools"])
    skill_suffix = " Load this skill for scoped sessions." if skill else ""
    skills_block = _skills_yaml(list(skills))  # type: ignore[arg-type]
    return (
        f"---\n"
        f"name: {template_id}\n"
        f"description: |\n"
        f"  {description}{skill_suffix}\n"
        f"model: inherit\n"
        f"tools: {tools}\n"
        f"{skills_block}"
        f"---\n\n"
    )


def write_template(spec: dict[str, object]) -> None:
    template_id = str(spec["id"])
    target = TEMPLATES_ROOT / template_id
    target.mkdir(parents=True, exist_ok=True)
    body = _body(spec)
    (target / "body.md.tpl").write_text(body, encoding="utf-8")

    skills = spec.get("recommended_skills", [])
    external = spec.get("external_skills", [])
    yaml_parts = [
        'schema_version: "1.0"',
        f"id: {template_id}",
        f"label: {spec['label']}",
        "description: |",
        f"  {str(spec['description']).strip()}",
        f"archetype: {spec['archetype']}",
        f"scope: {spec['scope']}",
        "status: stable",
        "version: 1.0.0",
        "prompt_kinds:",
    ]
    for kind in spec["prompt_kinds"]:  # type: ignore[index]
        yaml_parts.append(f"  - {kind}")
    mcp_tools = list(spec["mcp_tools"])  # type: ignore[arg-type]
    if mcp_tools:
        yaml_parts.append("mcp_tools:")
        for tool in mcp_tools:
            yaml_parts.append(f"  - {tool}")
    else:
        yaml_parts.append("mcp_tools: []")
    delegates_to = list(spec["delegates_to"])  # type: ignore[arg-type]
    if delegates_to:
        yaml_parts.append("delegates_to:")
        for child in delegates_to:
            yaml_parts.append(f"  - {child}")
    else:
        yaml_parts.append("delegates_to: []")
    yaml_parts.append("delegated_by:")
    for parent in spec["delegated_by"]:  # type: ignore[index]
        yaml_parts.append(f"  - {parent}")
    yaml_parts.extend(
        [
            "ui:",
            f"  category: {spec['category']}",
            f"  sort_order: {spec['sort_order']}",
            PROMPTS_BLOCK.strip(),
        ]
    )
    skill_list = list(skills) if skills else []  # type: ignore[arg-type]
    if skill_list:
        yaml_parts.append("recommended_skills:")
        for skill_name in skill_list:
            yaml_parts.append(f"  - {skill_name}")
    else:
        yaml_parts.append("recommended_skills: []")
    if external:
        yaml_parts.append("external_skills:")
        for item in external:  # type: ignore[union-attr]
            yaml_parts.append(f"  - name: {item['name']}")
            yaml_parts.append(f"    note: {item['note']}")
    yaml_parts.append("vendors:")
    yaml_parts.extend(VENDOR_BLOCK.format(id=template_id).splitlines())
    yaml_parts.extend(FILE_BLOCK.format(id=template_id).splitlines())
    (target / "template.yaml").write_text(
        "\n".join(yaml_parts) + "\n", encoding="utf-8"
    )

    default_tpl = _frontmatter(spec) + '{{ include "body" }}\n'
    (target / f"{template_id}.md.tpl").write_text(default_tpl, encoding="utf-8")
    skill_tpl = _frontmatter(spec, skill=True) + '{{ include "body" }}\n'
    (target / f"{template_id}.skill.md.tpl").write_text(skill_tpl, encoding="utf-8")

    for suffix in ("cursor", "opencode", "github-copilot.agent"):
        source_name = f"orchestration-overseer.{suffix}.md.tpl"
        source = OVERSEER / source_name
        if not source.is_file():
            continue
        content = source.read_text(encoding="utf-8")
        content = content.replace("orchestration-overseer", template_id)
        content = content.replace("Orchestration overseer", str(spec["role_heading"]))
        if "{{ include" not in content:
            content = _frontmatter(spec) + '{{ include "body" }}\n'
        (target / f"{template_id}.{suffix}.md.tpl").write_text(
            content, encoding="utf-8"
        )

    for fragment in ("AGENTS.md.fragment.tpl", "manifest.json.tpl"):
        shutil.copy2(OVERSEER / fragment, target / fragment)


def main() -> int:
    for spec in SPECS:
        write_template(spec)
        print(f"scaffolded {spec['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
