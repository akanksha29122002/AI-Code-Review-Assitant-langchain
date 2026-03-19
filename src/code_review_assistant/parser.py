from __future__ import annotations

import re


def normalize_diff(diff_text: str) -> str:
    """Trim surrounding whitespace while preserving the diff body."""
    return diff_text.strip()


def normalize_list(items: list[str]) -> str:
    if not items:
        return "None provided."
    return ", ".join(item.strip() for item in items if item.strip()) or "None provided."


def parse_line_reference(raw_line_reference: str | None) -> int | None:
    if not raw_line_reference:
        return None
    match = re.search(r"\d+", raw_line_reference)
    if not match:
        return None
    return int(match.group())


def extract_added_lines(patch: str) -> set[int]:
    added_lines: set[int] = set()
    current_line = 0
    for line in patch.splitlines():
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line = int(match.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.add(current_line)
            current_line += 1
            continue
        if line.startswith("-") and not line.startswith("---"):
            continue
        current_line += 1
    return added_lines
