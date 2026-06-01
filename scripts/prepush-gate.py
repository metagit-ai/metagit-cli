#!/usr/bin/env python3
"""Cross-agent pre-push quality gate runner."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run_step(name: str, cmd: list[str], logs_dir: Path, shell: bool = False) -> bool:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{name}.log"
    print(f"==> {name}")
    with log_path.open("w", encoding="utf-8") as log_file:
        completed = subprocess.run(
            cmd if not shell else " ".join(cmd),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            shell=shell,
            text=True,
            check=False,
        )
    if completed.returncode == 0:
        print(f"PASS: {name}")
        return True
    print(f"FAIL: {name}")
    print(f"--- last output ({log_path}) ---")
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-40:]:
        print(line)
    print("--- end output ---")
    return False


def resolve_manifest_fixture_cmd() -> list[str]:
    if shutil.which("uv"):
        return ["uv", "run", "python", "scripts/validate-manifest-fixtures.py"]
    return [sys.executable, "scripts/validate-manifest-fixtures.py"]


def resolve_pytest_cmd() -> list[str]:
    if shutil.which("uv"):
        return ["uv", "run", "pytest", "tests/integration", "-v"]
    return [sys.executable, "-m", "pytest", "tests/integration", "-v"]


SECURITY_DEP_FILES = frozenset({"pyproject.toml", "uv.lock"})
SECURITY_SRC_PREFIX = "src/"


def _git_lines(args: list[str]) -> list[str] | None:
    if not shutil.which("git") or not Path(".git").exists():
        return None
    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def changed_paths_for_security() -> set[str] | None:
    """Collect changed paths; None means run the full security pipeline."""
    chunks: list[str] = []
    for spec in (
        ["diff", "--name-only", "HEAD"],
        ["diff", "--cached", "--name-only"],
    ):
        lines = _git_lines(spec)
        if lines is None:
            return None
        chunks.extend(lines)
    upstream = _git_lines(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if upstream:
        branch_diff = _git_lines(["diff", "--name-only", f"{upstream[0]}...HEAD"])
        if branch_diff is None:
            return None
        chunks.extend(branch_diff)
    return set(chunks)


def security_scan_plan(changed: set[str] | None) -> tuple[bool, bool, bool]:
    """Return (sync_deps, pip_audit, bandit) for context-aware security."""
    if changed is None or not changed:
        return (True, True, True)
    deps = any(path in SECURITY_DEP_FILES for path in changed)
    src = any(path.startswith(SECURITY_SRC_PREFIX) for path in changed)
    if deps:
        return (True, True, True)
    if src:
        return (False, True, True)
    return (False, False, False)


def run_security_scan(logs_dir: Path) -> bool:
    """Run pip-audit/bandit when lockfile or src/ changed; skip for docs-only diffs."""
    changed = changed_paths_for_security()
    sync_deps, pip_audit, bandit = security_scan_plan(changed)
    if not (sync_deps or pip_audit or bandit):
        print("SKIP: security_scan (no changes under src/, pyproject.toml, or uv.lock)")
        return True

    failed = False
    if sync_deps:
        failed |= not run_step(
            "security_sync",
            ["uv", "sync", "--frozen", "--all-extras"],
            logs_dir,
        )
    if pip_audit:
        failed |= not run_step("security_audit", ["uv", "run", "pip-audit"], logs_dir)
    if bandit:
        failed |= not run_step(
            "security_bandit",
            ["uv", "run", "bandit", "-r", "src", "-ll"],
            logs_dir,
        )
    return not failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if args.rounds < 1:
        print("ERROR: --rounds must be >= 1")
        return 2

    if not Path("Taskfile.yml").exists():
        print("ERROR: run this script from repo root")
        return 2

    if not shutil.which("task"):
        print("ERROR: task is required but not found in PATH")
        return 2

    logs_dir = Path(".metagit")
    round_idx = 1
    while True:
        print(f"\n### QA ROUND {round_idx} ###")
        failed = False

        failed |= not run_step("format", ["task", "format"], logs_dir)
        failed |= not run_step("lint_fix", ["task", "lint:fix"], logs_dir)
        failed |= not run_step("lint", ["task", "lint"], logs_dir)
        failed |= not run_step(
            "manifest_fixtures",
            resolve_manifest_fixture_cmd(),
            logs_dir,
        )
        failed |= not run_step("unit_tests", ["task", "test"], logs_dir)
        failed |= not run_step("e2e_tests", resolve_pytest_cmd(), logs_dir)
        failed |= not run_security_scan(logs_dir)

        if shutil.which("gitleaks"):
            security_ok = run_step(
                "security_gitleaks", ["task", "secret:search"], logs_dir
            )
            if args.strict and not security_ok:
                failed = True
        else:
            print("SKIP: security_gitleaks (gitleaks not installed)")

        if not failed:
            print(f"ROUND {round_idx}: PASS")
            print("\nAll pre-push checks passed.")
            return 0

        print(f"ROUND {round_idx}: FAIL")
        if not args.loop or round_idx >= args.rounds:
            print(f"\nStopped after {round_idx} round(s) with failures.")
            return 1
        round_idx += 1
        print("\nRetrying QA pipeline...")


if __name__ == "__main__":
    raise SystemExit(main())
