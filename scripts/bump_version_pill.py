#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TARGET = ROOT_DIR / "app" / "templates" / "base.html"


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
    replacement = f"{match.group(1)}{new_version}{match.group(4)}"

    updated = text[: match.start()] + replacement + text[match.end() :]
    TARGET.write_text(updated, encoding="utf-8")
    print(f"{new_version} (was {old_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
