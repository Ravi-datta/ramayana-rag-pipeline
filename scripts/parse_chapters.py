from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.io.readers import read_jsonl
from ramayana_rag.parsing.chapter_parser import build_chapters_from_toc, write_chapters_json
from ramayana_rag.parsing.toc_parser import parse_toc_entries


def main() -> None:
    pages = read_jsonl("data/extracted/pages_clean.jsonl")
    toc_entries = parse_toc_entries(pages)

    chapters = build_chapters_from_toc(pages, toc_entries)
    write_chapters_json(chapters, "data/intermediate/chapters_telugu.json")

    detected = {chapter["chapter_number"] for chapter in chapters}
    missing = [num for num in range(1, 100) if num not in detected]
    needs_review = [
        chapter["chapter_number"]
        for chapter in chapters
        if chapter.get("needs_review")
    ]

    print(f"TOC entries: {len(toc_entries)}")
    print(f"Chapters parsed: {len(chapters)}")
    print(f"Missing chapters: {missing}")
    print(f"Chapters needing review: {needs_review}")

    print("\nFirst chapter:")
    first = chapters[0]
    print(
        {
            "chapter_number": first["chapter_number"],
            "chapter_id": first["chapter_id"],
            "kanda_english": first["kanda_english"],
            "sarga_range": first["sarga_range"],
            "source_pdf_pages": first["source_pdf_pages"],
            "printed_page_numbers": first["printed_page_numbers"],
            "text_chars": len(first["raw_telugu_text"]),
            "parser_warnings": first["parser_warnings"],
        }
    )

    print("\nLast chapter:")
    last = chapters[-1]
    print(
        {
            "chapter_number": last["chapter_number"],
            "chapter_id": last["chapter_id"],
            "kanda_english": last["kanda_english"],
            "sarga_range": last["sarga_range"],
            "source_pdf_pages": last["source_pdf_pages"],
            "printed_page_numbers": last["printed_page_numbers"],
            "text_chars": len(last["raw_telugu_text"]),
            "parser_warnings": last["parser_warnings"],
        }
    )


if __name__ == "__main__":
    main()
