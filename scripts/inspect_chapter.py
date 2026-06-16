from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect parsed Telugu chapter text.")
    parser.add_argument("--chapter", type=int, required=True, help="Chapter number to inspect.")
    parser.add_argument("--chars", type=int, default=2500, help="Number of characters to print.")
    args = parser.parse_args()

    path = Path("data/intermediate/chapters_telugu.json")

    if not path.exists():
        raise FileNotFoundError("Missing data/intermediate/chapters_telugu.json")

    with path.open("r", encoding="utf-8") as f:
        chapters = json.load(f)

    chapter = next(
        (item for item in chapters if int(item["chapter_number"]) == args.chapter),
        None,
    )

    if chapter is None:
        raise ValueError(f"Chapter not found: {args.chapter}")

    text = chapter.get("raw_telugu_text", "")

    print({
        "chapter_number": chapter["chapter_number"],
        "chapter_id": chapter["chapter_id"],
        "kanda_telugu": chapter["kanda_telugu"],
        "chapter_title_telugu": chapter["chapter_title_telugu"],
        "sarga_range": chapter["sarga_range"],
        "source_pdf_pages": chapter["source_pdf_pages"],
        "printed_page_numbers": chapter["printed_page_numbers"],
        "text_chars": len(text),
        "question_count": len(chapter.get("questions", [])),
        "parser_warnings": chapter.get("parser_warnings", []),
    })

    print("\n--- TEXT START ---")
    print(text[: args.chars])
    print("\n--- TEXT END PREVIEW ---")
    print(text[-args.chars:])


if __name__ == "__main__":
    main()
