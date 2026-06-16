from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.translation.chapter_translator import ChapterTranslator, TranslationRunError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Ramayana RAG pipeline translation phase."
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Accepted for pipeline command compatibility; extraction is not run here.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Accepted for pipeline command compatibility; processed outputs are not built here.",
    )
    parser.add_argument(
        "--chapters",
        nargs="+",
        type=int,
        help="Specific chapter numbers to translate. Omit to translate all parsed chapters.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-translate chapters even when per-chapter cache files already exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    translator = ChapterTranslator(
        input_path=ROOT / "data/intermediate/chapters_telugu.json",
        cache_dir=ROOT / "data/intermediate/translated_chapters",
        combined_output_path=ROOT / "data/intermediate/chapters_english.json",
        audit_output_path=ROOT / "data/intermediate/translation_audit.jsonl",
    )

    try:
        result = translator.translate(chapter_numbers=args.chapters, force=args.force)
    except TranslationRunError as exc:
        print(str(exc), file=sys.stderr)
        print(
            "See data/intermediate/translation_audit.jsonl for per-chapter failure details.",
            file=sys.stderr,
        )
        return 1

    translated = sum(1 for record in result.audit_records if record["status"] == "translated")
    cached = sum(1 for record in result.audit_records if record["status"] == "cached")

    print(f"Translation phase complete: {len(result.translated_chapters)} chapter(s).")
    print(f"Translated via DeepSeek: {translated}")
    print(f"Loaded from cache: {cached}")
    print("Combined output: data/intermediate/chapters_english.json")
    print("Audit log: data/intermediate/translation_audit.jsonl")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
