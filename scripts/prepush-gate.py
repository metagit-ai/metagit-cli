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


def resolve_pytest_cmd() -> list[str]:
    if shutil.which("uv"):
        return ["uv", "run", "pytest", "tests/integration", "-v"]
    return [sys.executable, "-m", "pytest", "tests/integration", "-v"]


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
        failed |= not run_step("unit_tests", ["task", "test"], logs_dir)
        failed |= not run_step("e2e_tests", resolve_pytest_cmd(), logs_dir)

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
