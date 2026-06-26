#!/usr/bin/env python3
"""
Audit and scaffold agent-access artifacts for a repository.

Usage:
  optimize_agent_access.py REPO_ROOT [--apply] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

MARKER_START = "<!-- agent-access:start"
MARKER_END = "agent-access:end -->"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "templates"


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _detect_project(repo: Path) -> dict[str, str]:
    name = repo.name
    cli = name
    install = "see README"
    session = "see README"
    extra_rows: list[str] = []

    if (repo / "pyproject.toml").is_file():
        install = "uv sync  # or: uv tool install <pypi-name>"
        session = "uv run <entrypoint> --help"
        extra_rows.append("| Tests | `task test` or `uv run pytest` |")
        try:
            text = (repo / "pyproject.toml").read_text(encoding="utf-8")
            match = re.search(r'name\s*=\s*"([^"]+)"', text)
            if match:
                cli = match.group(1)
        except OSError:
            pass
    elif (repo / "package.json").is_file():
        install = "npm install"
        session = "npm test  # verify"
        extra_rows.append("| Dev | `npm run dev` |")
    elif (repo / "go.mod").is_file():
        install = "go build ./..."
        session = "go test ./..."

    if (repo / ".metagit.yml").is_file():
        session = "export METAGIT_AGENT_MODE=true\nmetagit context pack --tier 2 --json"
        extra_rows.append("| Metagit skills | `metagit skills install --scope user` |")

    if (repo / "Taskfile.yml").is_file() or (repo / "Taskfile.yaml").is_file():
        extra_rows.append("| QA | `task qa:prepush` |")

    description = "Software project."
    readme = _read_text(repo / "README.md")
    if readme:
        for line in readme.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("["):
                description = stripped[:200]
                break

    return {
        "project_name": name,
        "one_line_description": description,
        "install_cmd": install,
        "session_cmds": session,
        "cli_name": cli,
        "extra_cmd_rows": "\n".join(extra_rows),
        "docs_agents_link": "- [docs/agents.md](docs/agents.md)" if (repo / "docs").is_dir() else "",
        "optional_section": "- Contributor docs: see README",
    }


def _fill_template(name: str, ctx: dict[str, str]) -> str:
    raw = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    session_lines = [line.strip() for line in ctx["session_cmds"].split("\n") if line.strip()]
    session_json = ", ".join(json.dumps(line) for line in session_lines) or '""'
    mapping = {
        "{{PROJECT_NAME}}": ctx["project_name"],
        "{{ONE_LINE_DESCRIPTION}}": ctx["one_line_description"],
        "{{INSTALL_CMD}}": ctx["install_cmd"],
        "{{SESSION_CMDS}}": ctx["session_cmds"],
        "{{CLI_NAME}}": ctx["cli_name"],
        "{{EXTRA_CMD_ROWS}}": ctx["extra_cmd_rows"],
        "{{DOCS_AGENTS_LINK}}": ctx["docs_agents_link"],
        "{{OPTIONAL_SECTION}}": ctx["optional_section"],
        "{{SESSION_JSON_ARRAY}}": session_json,
    }
    for token, value in mapping.items():
        raw = raw.replace(token, value)
    return raw


def _html_comment_block(ctx: dict[str, str]) -> str:
    session_one = ctx["session_cmds"].replace("\n", " && ")
    return (
        f"{MARKER_START}\n"
        f"project: {ctx['project_name']}\n"
        f"install: {ctx['install_cmd']}\n"
        f"session_start: {session_one}\n"
        f"refs: llms.txt, AGENTS.md\n"
        f"{MARKER_END}\n"
    )


def audit(repo: Path) -> dict[str, Any]:
    readme = _read_text(repo / "README.md") or ""
    return {
        "repo_root": str(repo.resolve()),
        "has_llms_txt": (repo / "llms.txt").is_file(),
        "has_agents_md": (repo / "AGENTS.md").is_file(),
        "has_docs_agents": (repo / "docs" / "agents.md").is_file(),
        "has_readme_agent_comment": MARKER_START in readme,
        "has_dot_agent_manifest": (repo / ".agent" / "manifest.json").is_file(),
        "has_mkdocs": (repo / "mkdocs.yml").is_file(),
        "has_metagit": (repo / ".metagit.yml").is_file(),
    }


def apply(repo: Path, ctx: dict[str, str]) -> list[str]:
    changed: list[str] = []
    llms_path = repo / "llms.txt"
    if not llms_path.is_file():
        llms_path.write_text(_fill_template("llms.txt.template", ctx), encoding="utf-8")
        changed.append(str(llms_path))

    agents_path = repo / "AGENTS.md"
    if not agents_path.is_file():
        agents_path.write_text(_fill_template("AGENTS.md.template", ctx), encoding="utf-8")
        changed.append(str(agents_path))

    agent_dir = repo / ".agent"
    manifest_path = agent_dir / "manifest.json"
    if not manifest_path.is_file():
        agent_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            _fill_template("agent-manifest.json.template", ctx),
            encoding="utf-8",
        )
        changed.append(str(manifest_path))

    readme_path = repo / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        if MARKER_START not in readme:
            block = _html_comment_block(ctx)
            lines = readme.splitlines()
            insert_at = 1
            for idx, line in enumerate(lines):
                if line.startswith("#"):
                    insert_at = idx + 1
                    break
            lines.insert(insert_at, "")
            lines.insert(insert_at + 1, block.rstrip())
            readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            changed.append(str(readme_path))

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimize agent access artifacts")
    parser.add_argument("repo_root", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo = args.repo_root.expanduser().resolve()
    if not repo.is_dir():
        print(f"ERROR: not a directory: {repo}", file=sys.stderr)
        return 2

    report = audit(repo)
    ctx = _detect_project(repo)
    gaps = [
        key
        for key, present in [
            ("llms.txt", report["has_llms_txt"]),
            ("AGENTS.md", report["has_agents_md"]),
            ("README HTML comment", report["has_readme_agent_comment"]),
            (".agent/manifest.json", report["has_dot_agent_manifest"]),
        ]
        if not present
    ]
    report["gaps"] = gaps
    report["detected"] = ctx

    if args.apply and gaps:
        report["files_changed"] = apply(repo, ctx)
        refreshed = audit(repo)
        report["gaps_after"] = [
            label
            for label, ok in [
                ("llms.txt", refreshed["has_llms_txt"]),
                ("AGENTS.md", refreshed["has_agents_md"]),
                ("README HTML comment", refreshed["has_readme_agent_comment"]),
            ]
            if not ok
        ]
        exit_code = 1 if report["gaps_after"] else 0
    else:
        report["files_changed"] = []
        exit_code = 0

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Repo: {repo}")
        print(f"Gaps: {', '.join(gaps) if gaps else 'none'}")
        if report.get("files_changed"):
            print("Changed:", ", ".join(report["files_changed"]))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
