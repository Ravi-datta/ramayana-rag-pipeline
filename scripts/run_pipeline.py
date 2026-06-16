from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.chunking.chunk_builder import build_chunks_file, chunk_counts_by_type
from ramayana_rag.entities.entity_resolver import normalize_entities_file
from ramayana_rag.translation.chapter_translator import ChapterTranslator, TranslationRunError
from ramayana_rag.validation.reports import build_markdown_preview, write_validation_report


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

    normalization = normalize_entities_file(
        input_path=ROOT / "data/intermediate/chapters_english.json",
        output_path=ROOT / "data/intermediate/chapters_english_normalized.json",
        aliases_path=ROOT / "configs/entity_aliases.yaml",
        audit_output_path=ROOT / "data/intermediate/entity_normalization_audit.json",
    )
    print(f"Entity normalization complete: {len(normalization.chapters)} chapter(s).")
    print("Normalized output: data/intermediate/chapters_english_normalized.json")
    print("Entity audit: data/intermediate/entity_normalization_audit.json")

    chunk_result = build_chunks_file(
        input_path=ROOT / "data/intermediate/chapters_english_normalized.json",
        output_dir=ROOT / args.output_dir,
    )
    print(f"Chunk generation complete: {len(chunk_result.chunks)} chunk(s).")
    print(f"Chunk counts by type: {chunk_counts_by_type(chunk_result.chunks)}")
    print("Chunks JSONL: data/processed/final_chunks.jsonl")
    print("Chunks JSON: data/processed/final_chunks.json")
    print("Chapter index: data/processed/chapter_index.csv")

    output_dir = ROOT / args.output_dir
    validation_report = write_validation_report(
        output_path=output_dir / "validation_report.json",
        chunks_json_path=output_dir / "final_chunks.json",
        chunks_jsonl_path=output_dir / "final_chunks.jsonl",
        chapter_index_path=output_dir / "chapter_index.csv",
    )
    print(f"Validation report complete with {len(validation_report['warnings'])} warning(s).")
    print("Validation report: data/processed/validation_report.json")

    preview = build_markdown_preview(
        validation_report_path=output_dir / "validation_report.json",
        output_path=output_dir / "final_chunks_preview.md",
    )
    print(f"Markdown preview complete: {len(preview)} characters.")
    print("Preview: data/processed/final_chunks_preview.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
