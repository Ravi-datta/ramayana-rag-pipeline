from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz


PRINTED_PAGE_PATTERN = re.compile(r"^\s*(\d{1,4})\s*$")


def detect_printed_page_number(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return None

    candidates = []

    # Printed page numbers usually appear near the top or bottom.
    candidates.extend(lines[:5])
    candidates.extend(lines[-5:])

    for line in candidates:
        match = PRINTED_PAGE_PATTERN.match(line)
        if match:
            return match.group(1)

    return None


def extract_pdf_pages(pdf_path: str | Path) -> list[dict[str, Any]]:
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    records: list[dict[str, Any]] = []

    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            raw_text = page.get_text("text")

            records.append(
                {
                    "pdf_page_index": page_index,
                    "printed_page_number": detect_printed_page_number(raw_text),
                    "raw_text": raw_text,
                    "extraction_method": "pymupdf",
                }
            )

    return records
