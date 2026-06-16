from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.extraction.page_cleaner import clean_pages
from ramayana_rag.io.readers import read_jsonl
from ramayana_rag.io.writers import write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean extracted PDF page text.")
    parser.add_argument(
        "--input",
        default="data/extracted/pages.jsonl",
        help="Input extracted pages JSONL.",
    )
    parser.add_argument(
        "--output",
        default="data/extracted/pages_clean.jsonl",
        help="Output cleaned pages JSONL.",
    )

    args = parser.parse_args()

    records = read_jsonl(args.input)
    cleaned = clean_pages(records)
    write_jsonl(cleaned, args.output)

    non_empty = sum(1 for record in cleaned if record["clean_text"].strip())

    print(f"Input pages: {len(records)}")
    print(f"Cleaned pages: {len(cleaned)}")
    print(f"Pages with cleaned text: {non_empty}")
    print(f"Output written to: {args.output}")

    if cleaned:
        print("\nFirst cleaned page preview:")
        print(cleaned[0]["clean_text"][:500])

        print("\nFirst content page preview:")
        for record in cleaned:
            if "ప్రశ్న" in record["clean_text"]:
                print(record["clean_text"][:1000])
                break


if __name__ == "__main__":
    main()
