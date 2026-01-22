from __future__ import annotations

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
