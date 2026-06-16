from __future__ import annotations

from typing import Any


REQUIRED_NORMALIZED_CHAPTER_FIELDS = {
    "chapter_number",
    "chapter_id",
    "kanda",
    "kanda_order",
    "sarga_range",
    "chapter_title",
    "chapter_summary",
    "questions",
    "canonical_entities",
    "entity_mentions",
    "places",
    "themes",
    "source_pdf_pages",
    "printed_page_numbers",
}

REQUIRED_CHUNK_FIELDS = {"chunk_id", "text", "metadata"}

REQUIRED_CHUNK_METADATA_FIELDS = {
    "document_title",
    "source_file",
    "language_original",
    "language_output",
    "kanda",
    "kanda_order",
    "chapter_number",
    "chapter_title",
    "sarga_range",
    "question_number",
    "chunk_type",
    "answer_type",
    "canonical_entities",
    "entity_mentions",
    "places",
    "themes",
    "source_pdf_pages",
    "printed_page_numbers",
    "translation_model",
    "pipeline_version",
}

QA_CHUNK_TYPES = {
    "qa_multiple_choice",
    "qa_direct_answer",
    "qa_narrative",
    "qa_narrative_part",
}


def missing_fields(record: dict[str, Any], required_fields: set[str]) -> list[str]:
    return sorted(field for field in required_fields if field not in record)


def validate_normalized_chapter_schema(chapter: dict[str, Any]) -> list[str]:
    errors = missing_fields(chapter, REQUIRED_NORMALIZED_CHAPTER_FIELDS)
    if "questions" in chapter and not isinstance(chapter["questions"], list):
        errors.append("questions must be a list")
    return errors


def validate_chunk_schema(chunk: dict[str, Any]) -> tuple[list[str], list[str]]:
    root_missing = missing_fields(chunk, REQUIRED_CHUNK_FIELDS)
    metadata_missing: list[str] = []

    metadata = chunk.get("metadata")
    if isinstance(metadata, dict):
        metadata_missing = missing_fields(metadata, REQUIRED_CHUNK_METADATA_FIELDS)
    elif "metadata" not in root_missing:
        metadata_missing = ["metadata must be an object"]

    return root_missing, metadata_missing


def is_qa_chunk(chunk: dict[str, Any]) -> bool:
    metadata = chunk.get("metadata", {})
    if not isinstance(metadata, dict):
        return False
    return metadata.get("chunk_type") in QA_CHUNK_TYPES
