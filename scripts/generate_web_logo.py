#!/usr/bin/env python3
"""Generate a small header logo for the Metagit Web SPA from docs/inc source art."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "inc" / "metagit_logo_dark.png"
OUT_DIR = ROOT / "web" / "src" / "assets"
PNG_OUT = OUT_DIR / "metagit_logo_header.png"
WEBP_OUT = OUT_DIR / "metagit_logo_header.webp"
HEADER_PX = 128
WEBP_QUALITY = 85


def _outputs_fresh() -> bool:
    if not SOURCE.is_file() or not PNG_OUT.is_file():
        return False
    source_mtime = SOURCE.stat().st_mtime
    return PNG_OUT.stat().st_mtime >= source_mtime and (
        not WEBP_OUT.is_file() or WEBP_OUT.stat().st_mtime >= source_mtime
    )


def _resize_with_sips() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "sips",
            "-z",
            str(HEADER_PX),
            str(HEADER_PX),
            str(SOURCE),
            "--out",
            str(PNG_OUT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _resize_with_magick() -> None:
    magick = shutil.which("magick") or shutil.which("convert")
    if magick is None:
        raise RuntimeError("ImageMagick (magick/convert) not found")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            magick,
            str(SOURCE),
            "-resize",
            f"{HEADER_PX}x{HEADER_PX}",
            str(PNG_OUT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _write_webp() -> None:
    cwebp = shutil.which("cwebp")
    if cwebp is None:
        return
    subprocess.run(
        [cwebp, "-q", str(WEBP_QUALITY), str(PNG_OUT), "-o", str(WEBP_OUT)],
        check=True,
        capture_output=True,
        text=True,
    )


def generate(*, force: bool = False) -> int:
    if not SOURCE.is_file():
        print(f"ERROR: missing source logo: {SOURCE}", file=sys.stderr)
        return 1
    if not force and _outputs_fresh():
        print("Web header logo up to date")
        return 0

    try:
        if sys.platform == "darwin":
            _resize_with_sips()
        else:
            _resize_with_magick()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        if PNG_OUT.is_file() and not force:
            print(
                "WARN: could not regenerate logo; using committed web assets",
                file=sys.stderr,
            )
            return 0
        print(f"ERROR: logo resize failed: {exc}", file=sys.stderr)
        return 1

    try:
        _write_webp()
    except subprocess.CalledProcessError as exc:
        print(f"WARN: webp conversion skipped: {exc}", file=sys.stderr)

    print(f"Wrote {PNG_OUT.relative_to(ROOT)}")
    if WEBP_OUT.is_file():
        print(f"Wrote {WEBP_OUT.relative_to(ROOT)}")
    return 0


def main() -> int:
    force = "--force" in sys.argv
    return generate(force=force)


if __name__ == "__main__":
    raise SystemExit(main())
