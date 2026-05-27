#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
FORCE="${2:-false}"
TARGET="$ROOT/.metagit.yml"

uv run python - "$ROOT" "$TARGET" "$FORCE" <<'PY'
import sys
from pathlib import Path

from metagit.core.config.manager import MetagitConfigManager, create_metagit_config
from metagit.core.config.manifest_gate import (
    ManifestGateInvalid,
    ManifestGateOutcome,
    evaluate_existing_manifest,
)

root = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()
force = sys.argv[3].lower() in {"1", "true", "yes", "force"}

gate = evaluate_existing_manifest(target, force=force)
if isinstance(gate, ManifestGateOutcome):
    print(f"status=exists\tvalidity=valid\tpath={target}")
    raise SystemExit(0)
if isinstance(gate, ManifestGateInvalid):
    print(f"status=exists\tvalidity=invalid\tpath={target}\tmessage={gate.error}")
    raise SystemExit(1)

yaml_out = create_metagit_config(name=root.name, kind="application", as_yaml=True)
if isinstance(yaml_out, Exception):
    print(f"status=error\tmessage={yaml_out}")
    raise SystemExit(1)

target.write_text(yaml_out, encoding="utf-8")
mgr = MetagitConfigManager(config_path=target)
result = mgr.load_config()
state = "valid" if not isinstance(result, Exception) else "invalid"
print(f"status=written\tvalidity={state}\tpath={target}")
if isinstance(result, Exception):
    raise SystemExit(1)
PY
