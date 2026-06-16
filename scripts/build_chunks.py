from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.chunking.chunk_builder import build_chunks_file, chunk_counts_by_type


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build semantic RAG chunks from normalized Ramayana chapters."
    )
    parser.add_argument(
        "--input",
        default=ROOT / "data/intermediate/chapters_english_normalized.json",
        type=Path,
        help="Normalized translated chapters JSON input.",
    )
    parser.add_argument(
        "--output-dir",
        default=ROOT / "data/processed",
        type=Path,
        help="Directory for final_chunks.jsonl, final_chunks.json, and chapter_index.csv.",
    )
    parser.add_argument(
        "--translation-model",
        default="deepseek-chat",
        help="Translation model metadata value to write into chunks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_chunks_file(
        input_path=args.input,
        output_dir=args.output_dir,
        translation_model=args.translation_model,
    )

    print(f"Chunk generation complete: {len(result.chunks)} chunk(s).")
    print(f"Chapter index rows: {len(result.chapter_index)}")
    print(f"Chunk counts by type: {chunk_counts_by_type(result.chunks)}")
    print("JSONL output: data/processed/final_chunks.jsonl")
    print("JSON output: data/processed/final_chunks.json")
    print("Chapter index: data/processed/chapter_index.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
