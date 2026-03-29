from __future__ import annotations

import re

PROJECT_COLOR_CHOICES: list[tuple[str, str]] = [
    ("slate", "Slate"),
    ("rose", "Rose"),
    ("sky", "Sky"),
    ("mint", "Mint"),
    ("amber", "Amber"),
    ("violet", "Violet"),
]


def normalize_project_color(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    allowed = {key for key, _ in PROJECT_COLOR_CHOICES}
    return cleaned if cleaned in allowed else None


_ACTION_STARTERS: set[str] = {
    "add",
    "align",
    "audit",
    "book",
    "build",
    "call",
    "clean",
    "clear",
    "close",
    "coach",
    "complete",
    "create",
    "cut",
    "define",
    "deliver",
    "design",
    "draft",
    "edit",
    "finish",
    "fix",
    "improve",
    "launch",
    "learn",
    "make",
    "map",
    "move",
    "organize",
    "organise",
    "plan",
    "prepare",
    "publish",
    "record",
    "reduce",
    "refine",
    "release",
    "remove",
    "repair",
    "replace",
    "research",
    "reset",
    "review",
    "schedule",
    "ship",
    "simplify",
    "sort",
    "start",
    "train",
    "update",
    "write",
}


def project_title_looks_action(title: str | None) -> bool:
    if not title:
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'/-]*", title.strip().lower())
    if len(words) < 2:
        return False
    first = words[0]
    if first in _ACTION_STARTERS:
        return True
    if first.endswith(("ize", "ise", "ify", "ate", "en")) and len(first) >= 5:
        return True
    return False
