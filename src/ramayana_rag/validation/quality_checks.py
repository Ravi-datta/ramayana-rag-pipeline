from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ramayana_rag.validation.schema_validator import (
    is_qa_chunk,
    validate_chunk_schema,
    validate_normalized_chapter_schema,
)


PIPELINE_VERSION = "1.0.0"
EXPECTED_CHAPTERS = 99
EXPECTED_QUESTIONS = 495
DEFAULT_TRANSLATION_MODEL = "deepseek-chat"


def load_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def count_jsonl_lines(path: str | Path) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def load_csv_rows(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_validation_report(
    chapters_telugu_path: str | Path = "data/intermediate/chapters_telugu.json",
    normalized_chapters_path: str | Path = "data/intermediate/chapters_english_normalized.json",
    chunks_json_path: str | Path = "data/processed/final_chunks.json",
    chunks_jsonl_path: str | Path = "data/processed/final_chunks.jsonl",
    chapter_index_path: str | Path = "data/processed/chapter_index.csv",
    translation_audit_path: str | Path = "data/intermediate/translation_audit.jsonl",
) -> dict[str, Any]:
    load_dotenv()

    telugu_chapters = load_json(chapters_telugu_path, default=[]) or []
    normalized_chapters = load_json(normalized_chapters_path, default=[]) or []
    chunks = load_json(chunks_json_path, default=[]) or []
    chapter_index_rows = load_csv_rows(chapter_index_path)
    translation_audit = load_jsonl(translation_audit_path)
    jsonl_line_count = count_jsonl_lines(chunks_jsonl_path)

    translation_model = detect_translation_model(chunks)

    parsing = validate_parsing(telugu_chapters)
    translation = validate_translation(normalized_chapters, translation_audit)
    chunking = validate_chunks(chunks, jsonl_line_count)
    entity_normalization = validate_entity_normalization(normalized_chapters, chunks)
    output_file_checks = validate_output_files(
        chunks_json_path=chunks_json_path,
        chunks_jsonl_path=chunks_jsonl_path,
        chapter_index_path=chapter_index_path,
        chapter_index_rows=chapter_index_rows,
    )

    warnings = collect_warnings(
        parsing=parsing,
        translation=translation,
        chunking=chunking,
        entity_normalization=entity_normalization,
        output_file_checks=output_file_checks,
    )

    return {
        "pipeline_version": PIPELINE_VERSION,
        "translation_model": translation_model,
        "parsing": parsing,
        "translation": translation,
        "chunking": chunking,
        "entity_normalization": entity_normalization,
        "output_file_checks": output_file_checks,
        "warnings": warnings,
    }


def validate_parsing(chapters: list[dict[str, Any]]) -> dict[str, Any]:
    detected_chapters = len(chapters)
    detected_numbers = {int(chapter.get("chapter_number")) for chapter in chapters}
    detected_questions = sum(len(chapter.get("questions", [])) for chapter in chapters)

    return {
        "expected_chapters": EXPECTED_CHAPTERS,
        "detected_chapters": detected_chapters,
        "expected_questions": EXPECTED_QUESTIONS,
        "detected_questions": detected_questions,
        "missing_chapters": [
            number for number in range(1, EXPECTED_CHAPTERS + 1) if number not in detected_numbers
        ],
        "chapters_with_question_count_issues": [
            {
                "chapter_number": chapter.get("chapter_number"),
                "question_count": len(chapter.get("questions", [])),
                "parser_warnings": chapter.get("parser_warnings", []),
            }
            for chapter in chapters
            if len(chapter.get("questions", [])) != 5
        ],
    }


def validate_translation(
    chapters: list[dict[str, Any]],
    translation_audit: list[dict[str, Any]],
) -> dict[str, Any]:
    missing_required: list[dict[str, Any]] = []
    missing_questions: list[int] = []

    for chapter in chapters:
        errors = validate_normalized_chapter_schema(chapter)
        if errors:
            missing_required.append(
                {
                    "chapter_number": chapter.get("chapter_number"),
                    "chapter_id": chapter.get("chapter_id"),
                    "missing_or_invalid_fields": errors,
                }
            )
        if not chapter.get("questions"):
            missing_questions.append(chapter.get("chapter_number"))

    failed_chapters = [
        {
            "chapter_number": record.get("chapter_number"),
            "chapter_id": record.get("chapter_id"),
            "error": record.get("error"),
        }
        for record in translation_audit
        if record.get("status") == "failed"
    ]

    return {
        "translated_chapters": len(chapters),
        "failed_chapters": failed_chapters,
        "chapters_missing_required_fields": missing_required,
        "chapters_missing_questions": missing_questions,
        "question_count_by_chapter": {
            str(chapter.get("chapter_number")): len(chapter.get("questions", []))
            for chapter in chapters
        },
    }


def validate_chunks(chunks: list[dict[str, Any]], jsonl_line_count: int) -> dict[str, Any]:
    chunks_missing_required_metadata: list[dict[str, Any]] = []
    empty_chunk_ids: list[dict[str, Any]] = []
    chunks_missing_question_text: list[str] = []
    chunks_missing_answer_text: list[str] = []

    for idx, chunk in enumerate(chunks):
        chunk_id = chunk.get("chunk_id")
        if not chunk_id:
            empty_chunk_ids.append({"index": idx, "chunk_id": chunk_id})

        root_missing, metadata_missing = validate_chunk_schema(chunk)
        if root_missing or metadata_missing:
            chunks_missing_required_metadata.append(
                {
                    "chunk_id": chunk_id,
                    "root_missing": root_missing,
                    "metadata_missing": metadata_missing,
                }
            )

        if is_qa_chunk(chunk):
            text = chunk.get("text", "")
            if "Question " not in text:
                chunks_missing_question_text.append(chunk_id or f"index_{idx}")
            if not any(label in text for label in ("Answer:", "Answer part:", "Correct answer:")):
                chunks_missing_answer_text.append(chunk_id or f"index_{idx}")

    return {
        "total_chunks": len(chunks),
        "chunk_counts_by_type": dict(
            Counter(
                chunk.get("metadata", {}).get("chunk_type", "unknown")
                for chunk in chunks
                if isinstance(chunk.get("metadata"), dict)
            )
        ),
        "empty_chunk_ids": empty_chunk_ids,
        "chunks_missing_required_metadata": chunks_missing_required_metadata,
        "chunks_missing_question_text": chunks_missing_question_text,
        "chunks_missing_answer_text": chunks_missing_answer_text,
        "json_jsonl_count_match": len(chunks) == jsonl_line_count,
        "json_chunk_count": len(chunks),
        "jsonl_line_count": jsonl_line_count,
    }


def validate_entity_normalization(
    chapters: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    chunks_with_canonical_entities = [
        chunk.get("chunk_id")
        for chunk in chunks
        if chunk.get("metadata", {}).get("canonical_entities")
    ]
    chunks_with_missing_canonical_entities = [
        chunk.get("chunk_id")
        for chunk in chunks
        if not chunk.get("metadata", {}).get("canonical_entities")
    ]

    candidates: dict[str, list[str]] = {}
    for chapter in chapters:
        unmapped = chapter.get("unmapped_entity_candidates", [])
        if unmapped:
            candidates[str(chapter.get("chapter_number"))] = unmapped

    return {
        "chunks_with_canonical_entities": len(chunks_with_canonical_entities),
        "chunks_with_missing_canonical_entities": chunks_with_missing_canonical_entities,
        "total_entity_mentions": sum(
            len(chunk.get("metadata", {}).get("entity_mentions", [])) for chunk in chunks
        ),
        "unmapped_entity_candidates": candidates,
    }


def validate_output_files(
    chunks_json_path: str | Path,
    chunks_jsonl_path: str | Path,
    chapter_index_path: str | Path,
    chapter_index_rows: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "final_chunks_json_exists": Path(chunks_json_path).exists(),
        "final_chunks_jsonl_exists": Path(chunks_jsonl_path).exists(),
        "chapter_index_csv_exists": Path(chapter_index_path).exists(),
        "chapter_index_rows": len(chapter_index_rows),
    }


def collect_warnings(
    parsing: dict[str, Any],
    translation: dict[str, Any],
    chunking: dict[str, Any],
    entity_normalization: dict[str, Any],
    output_file_checks: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []

    if parsing["detected_chapters"] != parsing["expected_chapters"]:
        warnings.append(
            f"Parsed chapter count is {parsing['detected_chapters']} "
            f"of expected {parsing['expected_chapters']}."
        )
    if parsing["detected_questions"] != parsing["expected_questions"]:
        warnings.append(
            f"Parsed question count is {parsing['detected_questions']} "
            f"of expected {parsing['expected_questions']}."
        )
    if translation["translated_chapters"] != parsing["expected_chapters"]:
        warnings.append(
            f"Only {translation['translated_chapters']} translated/normalized chapters are present; "
            "this is acceptable for the current sample run."
        )
    if translation["failed_chapters"]:
        warnings.append(f"Translation failures detected: {len(translation['failed_chapters'])}.")
    if chunking["chunks_missing_required_metadata"]:
        warnings.append("Some chunks are missing required metadata.")
    if chunking["chunks_missing_question_text"]:
        warnings.append("Some QA chunks are missing question text.")
    if chunking["chunks_missing_answer_text"]:
        warnings.append("Some QA chunks are missing answer text.")
    if not chunking["json_jsonl_count_match"]:
        warnings.append("final_chunks.json and final_chunks.jsonl counts do not match.")
    if entity_normalization["chunks_with_missing_canonical_entities"]:
        warnings.append("Some chunks have no canonical entities in metadata.")
    for key, exists in output_file_checks.items():
        if key.endswith("_exists") and not exists:
            warnings.append(f"Missing output file: {key}.")

    return warnings


def detect_translation_model(chunks: list[dict[str, Any]]) -> str:
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("translation_model"):
            return str(metadata["translation_model"])

    import os

    return os.getenv("DEEPSEEK_MODEL", DEFAULT_TRANSLATION_MODEL)
