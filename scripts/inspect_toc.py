from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.io.readers import read_jsonl
from ramayana_rag.parsing.toc_parser import parse_toc_entries


def main() -> None:
    pages = read_jsonl("data/extracted/pages_clean.jsonl")
    entries = parse_toc_entries(pages)

    print(f"TOC entries detected: {len(entries)}")

    print("\nFirst 10 entries:")
    for entry in entries[:10]:
        print(entry)

    print("\nLast 10 entries:")
    for entry in entries[-10:]:
        print(entry)

    detected_numbers = {entry["chapter_number"] for entry in entries}
    missing = [num for num in range(1, 100) if num not in detected_numbers]

    print(f"\nMissing chapter numbers from TOC: {missing}")


if __name__ == "__main__":
    main()
