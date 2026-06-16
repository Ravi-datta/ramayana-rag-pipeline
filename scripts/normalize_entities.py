from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.entities.entity_resolver import normalize_entities_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize entity metadata in translated Ramayana chapters."
    )
    parser.add_argument(
        "--input",
        default=ROOT / "data/intermediate/chapters_english.json",
        type=Path,
        help="Translated chapter JSON input.",
    )
    parser.add_argument(
        "--output",
        default=ROOT / "data/intermediate/chapters_english_normalized.json",
        type=Path,
        help="Normalized chapter JSON output.",
    )
    parser.add_argument(
        "--aliases",
        default=ROOT / "configs/entity_aliases.yaml",
        type=Path,
        help="Entity alias YAML config.",
    )
    parser.add_argument(
        "--audit-output",
        default=ROOT / "data/intermediate/entity_normalization_audit.json",
        type=Path,
        help="Entity normalization audit JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = normalize_entities_file(
        input_path=args.input,
        output_path=args.output,
        aliases_path=args.aliases,
        audit_output_path=args.audit_output,
    )

    print(f"Entity normalization complete: {len(result.chapters)} chapter(s).")
    print(f"Entity mentions: {result.audit['total_entity_mentions']}")
    print(f"Unmapped candidates: {result.audit['total_unmapped_entity_candidates']}")
    print("Output: data/intermediate/chapters_english_normalized.json")
    print("Audit: data/intermediate/entity_normalization_audit.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
