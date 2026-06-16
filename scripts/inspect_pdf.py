from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.extraction.pdf_extractor import extract_pdf_pages
from ramayana_rag.io.writers import write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and extract text from a PDF.")
    parser.add_argument("--pdf", required=True, help="Path to input PDF.")
    parser.add_argument(
        "--output",
        default="data/extracted/pages.jsonl",
        help="Output JSONL path.",
    )

    args = parser.parse_args()

    records = extract_pdf_pages(args.pdf)
    write_jsonl(records, args.output)

    non_empty_pages = sum(1 for record in records if record["raw_text"].strip())

    print(f"PDF path: {args.pdf}")
    print(f"Total pages extracted: {len(records)}")
    print(f"Pages with extractable text: {non_empty_pages}")
    print(f"Output written to: {args.output}")

    if records:
        first_text = records[0]["raw_text"].strip().replace("\n", " ")
        last_text = records[-1]["raw_text"].strip().replace("\n", " ")

        print("\nFirst page preview:")
        print(first_text[:500])

        print("\nLast page preview:")
        print(last_text[:500])


if __name__ == "__main__":
    main()
