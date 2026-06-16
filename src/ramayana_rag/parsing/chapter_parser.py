from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


KANDA_RANGES = [
    ("Bala Kanda", "బాల", 1, 13, 1),
    ("Ayodhya Kanda", "అయోధ్య", 14, 32, 2),
    ("Aranya Kanda", "అరణ్య", 33, 46, 3),
    ("Kishkindha Kanda", "కిష్కింధ", 47, 58, 4),
    ("Sundara Kanda", "సుందర", 59, 73, 5),
    ("Yuddha Kanda", "యుద్ధ", 74, 99, 6),
]


SARGA_LINE_RE = re.compile(r"^\s*[\d,\s]+సర్గలు\s*$")
CHAPTER_TITLE_RE = re.compile(r"అధ్యాయ")


def get_kanda_for_chapter(chapter_number: int) -> tuple[str, int]:
    for kanda_english, _kanda_telugu_hint, start, end, order in KANDA_RANGES:
        if start <= chapter_number <= end:
            return kanda_english, order

    raise ValueError(f"Chapter number outside expected range: {chapter_number}")


def normalize_chapter_id(kanda_english: str, chapter_number: int) -> str:
    prefix = {
        "Bala Kanda": "bala",
        "Ayodhya Kanda": "ayodhya",
        "Aranya Kanda": "aranya",
        "Kishkindha Kanda": "kishkindha",
        "Sundara Kanda": "sundara",
        "Yuddha Kanda": "yuddha",
    }[kanda_english]

    return f"{prefix}_{chapter_number:03d}"


def find_pdf_page_for_printed_page(
    pages: list[dict[str, Any]], printed_page_number: str
) -> int | None:
    for page in pages:
        if str(page.get("printed_page_number")) == str(printed_page_number):
            return int(page["pdf_page_index"])

    return None


def build_chapters_from_toc(
    pages: list[dict[str, Any]], toc_entries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []

    page_lookup = {
        int(page["pdf_page_index"]): page
        for page in pages
    }

    for idx, entry in enumerate(toc_entries):
        chapter_number = int(entry["chapter_number"])
        kanda_english, kanda_order = get_kanda_for_chapter(chapter_number)

        start_printed = entry.get("printed_page_number")
        next_printed = (
            toc_entries[idx + 1].get("printed_page_number")
            if idx + 1 < len(toc_entries)
            else None
        )

        start_pdf_page = (
            find_pdf_page_for_printed_page(pages, start_printed)
            if start_printed
            else None
        )
        next_pdf_page = (
            find_pdf_page_for_printed_page(pages, next_printed)
            if next_printed
            else None
        )

        parser_warnings: list[str] = []

        if start_pdf_page is None:
            parser_warnings.append(
                f"Could not map TOC printed page {start_printed} to PDF page."
            )
            continue

        if next_pdf_page is None:
            # Last chapter runs until end of document.
            end_pdf_page_exclusive = max(page_lookup) + 1
        else:
            end_pdf_page_exclusive = next_pdf_page

        source_pdf_pages = list(range(start_pdf_page, end_pdf_page_exclusive))

        page_texts = []
        printed_page_numbers = []

        for pdf_page_index in source_pdf_pages:
            page = page_lookup[pdf_page_index]
            page_texts.append(page.get("clean_text") or page.get("raw_text") or "")

            printed = page.get("printed_page_number")
            if printed is not None:
                printed_page_numbers.append(str(printed))

        raw_telugu_text = "\n\n".join(page_texts).strip()

        sarga_range = extract_sarga_range(raw_telugu_text)
        if not sarga_range:
            parser_warnings.append("Could not detect Sarga range.")

        chapters.append(
            {
                "chapter_number": chapter_number,
                "chapter_id": normalize_chapter_id(kanda_english, chapter_number),
                "kanda_telugu": entry["kanda_telugu"],
                "kanda_english": kanda_english,
                "kanda_order": kanda_order,
                "sarga_range": sarga_range,
                "chapter_title_telugu": entry["chapter_title_telugu"],
                "source_pdf_pages": source_pdf_pages,
                "printed_page_numbers": printed_page_numbers,
                "raw_telugu_text": raw_telugu_text,
                "questions": [],
                "parser_warnings": parser_warnings,
                "needs_review": bool(parser_warnings),
            }
        )

    return chapters


def extract_sarga_range(text: str) -> str | None:
    for line in text.splitlines():
        cleaned = line.strip()

        if SARGA_LINE_RE.match(cleaned):
            nums = re.findall(r"\d+", cleaned)
            if nums:
                return f"{nums[0]}-{nums[-1]}"

    return None


def write_chapters_json(chapters: list[dict[str, Any]], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)
