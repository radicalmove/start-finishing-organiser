#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TARGET = ROOT_DIR / "app" / "templates" / "base.html"
TAURI_CONFIG = ROOT_DIR / "src-tauri" / "tauri.conf.json"
CARGO_TOML = ROOT_DIR / "src-tauri" / "Cargo.toml"


def _replace_version(path: Path, pattern: re.Pattern, replacement: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(replacement, text, count=1)
    if count == 0:
        return False
    if updated != text:
        path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    pattern = re.compile(r'(class="version-pill[^"]*">)v(\d+)\.(\d+)(</span>)')
    text = TARGET.read_text(encoding="utf-8")
    match = pattern.search(text)
    if not match:
        print(f"Version pill not found in {TARGET}", file=sys.stderr)
        return 1

    major = int(match.group(2))
    minor_str = match.group(3)
    width = len(minor_str)
    minor = int(minor_str)

    minor += 1
    if minor >= 10**width:
        major += 1
        minor = 0

    old_version = f"v{match.group(2)}.{minor_str}"
    new_version = f"v{major}.{minor:0{width}d}"
    semver = f"{major}.{minor:0{width}d}.0"
    replacement = f"{match.group(1)}{new_version}{match.group(4)}"

    updated = text[: match.start()] + replacement + text[match.end() :]
    TARGET.write_text(updated, encoding="utf-8")
    tauri_updated = _replace_version(
        TAURI_CONFIG,
        re.compile(r'("version"\s*:\s*")[^"]+(")'),
        rf"\g<1>{semver}\2",
    )
    cargo_updated = _replace_version(
        CARGO_TOML,
        re.compile(r'^(version\s*=\s*")[^"]+(")', re.MULTILINE),
        rf"\g<1>{semver}\2",
    )

    print(f"{new_version} (was {old_version})")
    if tauri_updated or cargo_updated:
        print(f"Desktop version set to {semver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
