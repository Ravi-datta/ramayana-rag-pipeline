from __future__ import annotations

import re
from typing import Any


TOC_ENTRY_LINE_RE = re.compile(
    r"^\s*(?P<chapter_number>\d{1,3})\.\s*"
    r"(?P<kanda_telugu>.+?)\s*-\s*"
    r"(?P<chapter_title_telugu>.+?)\s*$"
)

PAGE_NUMBER_RE = re.compile(r"^\s*(?P<printed_page_number>\d{1,3})\s*$")


def parse_toc_entries(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    # Use raw_text here because clean_text removes standalone TOC page numbers.
    toc_lines: list[str] = []
    for page in pages[:8]:
        text = page.get("raw_text") or page.get("clean_text") or ""
        toc_lines.extend(line.strip() for line in text.splitlines() if line.strip())

    i = 0
    while i < len(toc_lines):
        line = toc_lines[i]
        match = TOC_ENTRY_LINE_RE.match(line)

        if not match:
            i += 1
            continue

        chapter_number = int(match.group("chapter_number"))

        if not 1 <= chapter_number <= 99:
            i += 1
            continue

        printed_page_number = None

        for j in range(i + 1, min(i + 5, len(toc_lines))):
            page_match = PAGE_NUMBER_RE.match(toc_lines[j])
            if page_match:
                printed_page_number = page_match.group("printed_page_number")
                break

        entries.append(
            {
                "chapter_number": chapter_number,
                "kanda_telugu": match.group("kanda_telugu").strip(),
                "chapter_title_telugu": match.group("chapter_title_telugu").strip(),
                "printed_page_number": printed_page_number,
            }
        )

        i += 1

    deduped: dict[int, dict[str, Any]] = {}
    for entry in entries:
        deduped.setdefault(entry["chapter_number"], entry)

    return [deduped[num] for num in sorted(deduped)]
