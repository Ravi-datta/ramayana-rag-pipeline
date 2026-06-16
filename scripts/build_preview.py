from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.validation.reports import build_markdown_preview, write_validation_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Markdown preview of final chunks.")
    parser.add_argument(
        "--output-dir",
        default=ROOT / "data/processed",
        type=Path,
        help="Processed output directory.",
    )
    parser.add_argument(
        "--normalized-chapters",
        default=ROOT / "data/intermediate/chapters_english_normalized.json",
        type=Path,
    )
    parser.add_argument(
        "--refresh-validation",
        action="store_true",
        help="Rebuild validation_report.json before generating the preview.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validation_report_path = args.output_dir / "validation_report.json"

    if args.refresh_validation or not validation_report_path.exists():
        write_validation_report(
            output_path=validation_report_path,
            normalized_chapters_path=args.normalized_chapters,
            chunks_json_path=args.output_dir / "final_chunks.json",
            chunks_jsonl_path=args.output_dir / "final_chunks.jsonl",
            chapter_index_path=args.output_dir / "chapter_index.csv",
        )

    markdown = build_markdown_preview(
        normalized_chapters_path=args.normalized_chapters,
        validation_report_path=validation_report_path,
        output_path=args.output_dir / "final_chunks_preview.md",
    )

    print("Markdown preview created: data/processed/final_chunks_preview.md")
    print(f"Preview characters: {len(markdown)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
