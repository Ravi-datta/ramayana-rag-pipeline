from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.validation.reports import write_validation_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Ramayana RAG validation report.")
    parser.add_argument(
        "--output-dir",
        default=ROOT / "data/processed",
        type=Path,
        help="Processed output directory containing final chunk artifacts.",
    )
    parser.add_argument(
        "--chapters-telugu",
        default=ROOT / "data/intermediate/chapters_telugu.json",
        type=Path,
    )
    parser.add_argument(
        "--normalized-chapters",
        default=ROOT / "data/intermediate/chapters_english_normalized.json",
        type=Path,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    report = write_validation_report(
        output_path=output_dir / "validation_report.json",
        chapters_telugu_path=args.chapters_telugu,
        normalized_chapters_path=args.normalized_chapters,
        chunks_json_path=output_dir / "final_chunks.json",
        chunks_jsonl_path=output_dir / "final_chunks.jsonl",
        chapter_index_path=output_dir / "chapter_index.csv",
    )

    print("Validation report created: data/processed/validation_report.json")
    print(f"Parsed chapters: {report['parsing']['detected_chapters']}")
    print(f"Translated/normalized chapters: {report['translation']['translated_chapters']}")
    print(f"Total chunks: {report['chunking']['total_chunks']}")
    print(f"Warnings: {len(report['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
