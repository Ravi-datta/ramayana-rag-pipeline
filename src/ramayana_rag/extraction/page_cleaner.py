from __future__ import annotations

import re
from typing import Any


STANDALONE_PAGE_NUMBER_RE = re.compile(r"^\s*\d{1,4}\s*$")
ROMAN_PAGE_RE = re.compile(r"^\s*[ivxlcdmIVXLCDM]{1,8}\s*$")
DOTTED_SEPARATOR_RE = re.compile(r"^\s*[.\-_=]{5,}\s*$")


def clean_page_text(text: str) -> str:
    cleaned_lines: list[str] = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            cleaned_lines.append("")
            continue

        # Remove standalone printed page numbers such as 11, 12, 249.
        if STANDALONE_PAGE_NUMBER_RE.match(line):
            continue

        # Remove roman front-matter page labels such as vii, viii, ix.
        if ROMAN_PAGE_RE.match(line):
            continue

        # Remove dotted separators.
        if DOTTED_SEPARATOR_RE.match(line):
            continue

        # Normalize internal whitespace without changing Telugu content.
        line = re.sub(r"\s+", " ", line)

        cleaned_lines.append(line)

    # Collapse excessive blank lines.
    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text.strip()


def clean_page_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        **record,
        "clean_text": clean_page_text(record.get("raw_text", "")),
    }


def clean_pages(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [clean_page_record(record) for record in records]
