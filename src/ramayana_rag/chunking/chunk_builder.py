from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ramayana_rag.chunking.token_utils import count_words, split_text_by_word_limit


DOCUMENT_TITLE = "Sri Ramayanamu - Prashnavali"
SOURCE_FILE = "ramayana.pdf"
LANGUAGE_ORIGINAL = "Telugu"
LANGUAGE_OUTPUT = "English"
PIPELINE_VERSION = "1.0.0"
DEFAULT_TRANSLATION_MODEL = "deepseek-chat"
IDEAL_MIN_WORDS = 350
IDEAL_MAX_WORDS = 750
MAX_CHUNK_WORDS = 1100


@dataclass(frozen=True)
class ChunkBuildResult:
    chunks: list[dict[str, Any]]
    chapter_index: list[dict[str, Any]]


def kanda_slug(kanda: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (kanda or "").lower()).strip("_")
    return cleaned.removesuffix("_kanda") or "unknown"


def build_chunks_from_chapters(
    chapters: list[dict[str, Any]],
    translation_model: str = DEFAULT_TRANSLATION_MODEL,
) -> ChunkBuildResult:
    chunks: list[dict[str, Any]] = []
    chapter_index: list[dict[str, Any]] = []

    for chapter in chapters:
        chapter_chunks = build_chapter_chunks(chapter, translation_model=translation_model)
        chunks.extend(chapter_chunks)
        chapter_index.append(build_chapter_index_row(chapter, chapter_chunks))

    return ChunkBuildResult(chunks=chunks, chapter_index=chapter_index)


def build_chapter_chunks(
    chapter: dict[str, Any],
    translation_model: str = DEFAULT_TRANSLATION_MODEL,
) -> list[dict[str, Any]]:
    chunks = [build_chapter_summary_chunk(chapter, translation_model=translation_model)]

    for question in chapter.get("questions", []):
        chunks.extend(build_question_chunks(chapter, question, translation_model=translation_model))

    return chunks


def build_chapter_summary_chunk(
    chapter: dict[str, Any],
    translation_model: str = DEFAULT_TRANSLATION_MODEL,
) -> dict[str, Any]:
    chapter_number = int(chapter["chapter_number"])
    slug = kanda_slug(chapter.get("kanda", ""))
    chunk_id = f"ramayana_{slug}_{chapter_number:03d}_summary"

    text = "\n".join(
        part
        for part in [
            f"Kanda: {chapter.get('kanda')}",
            f"Chapter {chapter_number}: {chapter.get('chapter_title')}",
            f"Sarga range: {chapter.get('sarga_range')}",
            _format_list("Primary entities", chapter.get("canonical_entities", [])),
            _format_list("Places", chapter.get("places", [])),
            _format_list("Themes", chapter.get("themes", [])),
            "",
            f"Summary: {chapter.get('chapter_summary', '')}",
        ]
        if part is not None
    ).strip()

    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": build_metadata(
            chapter=chapter,
            chunk_type="chapter_summary",
            answer_type=None,
            question=None,
            translation_model=translation_model,
        ),
    }


def build_question_chunks(
    chapter: dict[str, Any],
    question: dict[str, Any],
    translation_model: str = DEFAULT_TRANSLATION_MODEL,
) -> list[dict[str, Any]]:
    answer_type = question.get("answer_type", "")
    chunk_type = question_chunk_type(answer_type)
    base_text = build_question_text(chapter, question, chunk_type=chunk_type)

    if answer_type != "narrative" or count_words(base_text) <= MAX_CHUNK_WORDS:
        return [
            {
                "chunk_id": question_chunk_id(chapter, question),
                "text": base_text,
                "metadata": build_metadata(
                    chapter=chapter,
                    chunk_type=chunk_type,
                    answer_type=answer_type,
                    question=question,
                    translation_model=translation_model,
                ),
            }
        ]

    return build_split_narrative_chunks(chapter, question, translation_model=translation_model)


def build_split_narrative_chunks(
    chapter: dict[str, Any],
    question: dict[str, Any],
    translation_model: str = DEFAULT_TRANSLATION_MODEL,
) -> list[dict[str, Any]]:
    answer = question_answer_text(question)
    prefix = build_question_text(chapter, question, chunk_type="qa_narrative_part", answer_override="")
    prefix_words = count_words(prefix)
    answer_word_limit = max(100, MAX_CHUNK_WORDS - prefix_words - 30)
    answer_parts = split_text_by_word_limit(answer, answer_word_limit) or [answer]
    total_parts = len(answer_parts)
    chunks: list[dict[str, Any]] = []

    for idx, answer_part in enumerate(answer_parts, start=1):
        text = build_question_text(
            chapter,
            question,
            chunk_type="qa_narrative_part",
            answer_override=answer_part,
            part_number=idx,
            total_parts=total_parts,
        )
        chunks.append(
            {
                "chunk_id": question_chunk_id(chapter, question, part_number=idx),
                "text": text,
                "metadata": build_metadata(
                    chapter=chapter,
                    chunk_type="qa_narrative_part",
                    answer_type=question.get("answer_type"),
                    question=question,
                    translation_model=translation_model,
                ),
            }
        )

    return chunks


def build_question_text(
    chapter: dict[str, Any],
    question: dict[str, Any],
    chunk_type: str,
    answer_override: str | None = None,
    part_number: int | None = None,
    total_parts: int | None = None,
) -> str:
    chapter_number = int(chapter["chapter_number"])
    question_number = int(question["question_number"])
    answer = question_answer_text(question) if answer_override is None else answer_override

    lines = [
        f"Kanda: {chapter.get('kanda')}",
        f"Chapter {chapter_number}: {chapter.get('chapter_title')}",
        f"Sarga range: {chapter.get('sarga_range')}",
        _format_list("Primary entities", question.get("key_entities") or chapter.get("canonical_entities", [])),
        f"Question {question_number}: {question.get('question', '')}",
    ]

    if part_number is not None and total_parts is not None:
        lines.append(f"Part {part_number} of {total_parts}.")

    if question.get("answer_type") == "multiple_choice":
        lines.append("Options:")
        for option in question.get("options", []):
            if isinstance(option, dict):
                lines.append(f"{option.get('label')}. {option.get('text')}")
        lines.append(f"Correct answer: {question.get('correct_answer') or answer}")
    else:
        label = "Answer"
        if chunk_type == "qa_narrative_part":
            label = "Answer part"
        lines.append(f"{label}: {answer}")

    return "\n".join(line for line in lines if line is not None).strip()


def question_answer_text(question: dict[str, Any]) -> str:
    return str(question.get("answer") or question.get("correct_answer") or "").strip()


def question_chunk_type(answer_type: str) -> str:
    if answer_type == "multiple_choice":
        return "qa_multiple_choice"
    if answer_type == "direct_answer":
        return "qa_direct_answer"
    return "qa_narrative"


def question_chunk_id(
    chapter: dict[str, Any],
    question: dict[str, Any],
    part_number: int | None = None,
) -> str:
    chapter_number = int(chapter["chapter_number"])
    question_number = int(question["question_number"])
    base = f"ramayana_{kanda_slug(chapter.get('kanda', ''))}_{chapter_number:03d}_q{question_number:03d}"
    if part_number is not None:
        return f"{base}_part{part_number:02d}"
    return base


def build_metadata(
    chapter: dict[str, Any],
    chunk_type: str,
    answer_type: str | None,
    question: dict[str, Any] | None,
    translation_model: str,
) -> dict[str, Any]:
    question_entities = question.get("key_entities", []) if question else []
    question_mentions = question.get("entity_mentions", []) if question else []

    return {
        "document_title": DOCUMENT_TITLE,
        "source_file": SOURCE_FILE,
        "language_original": LANGUAGE_ORIGINAL,
        "language_output": LANGUAGE_OUTPUT,
        "kanda": chapter.get("kanda"),
        "kanda_order": chapter.get("kanda_order"),
        "chapter_number": chapter.get("chapter_number"),
        "chapter_title": chapter.get("chapter_title"),
        "sarga_range": chapter.get("sarga_range"),
        "question_number": question.get("question_number") if question else None,
        "chunk_type": chunk_type,
        "answer_type": answer_type,
        "canonical_entities": question_entities or chapter.get("canonical_entities", []),
        "entity_mentions": question_mentions or chapter.get("entity_mentions", []),
        "places": chapter.get("places", []),
        "themes": chapter.get("themes", []),
        "source_pdf_pages": chapter.get("source_pdf_pages", []),
        "printed_page_numbers": chapter.get("printed_page_numbers", []),
        "translation_model": translation_model,
        "pipeline_version": PIPELINE_VERSION,
    }


def build_chapter_index_row(
    chapter: dict[str, Any],
    chapter_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "chapter_number": chapter.get("chapter_number"),
        "chapter_id": chapter.get("chapter_id"),
        "kanda": chapter.get("kanda"),
        "kanda_order": chapter.get("kanda_order"),
        "chapter_title": chapter.get("chapter_title"),
        "sarga_range": chapter.get("sarga_range"),
        "source_pdf_pages": json.dumps(chapter.get("source_pdf_pages", []), ensure_ascii=False),
        "printed_page_numbers": json.dumps(
            chapter.get("printed_page_numbers", []),
            ensure_ascii=False,
        ),
        "question_count": len(chapter.get("questions", [])),
        "chunk_count": len(chapter_chunks),
        "chunk_ids": json.dumps(
            [chunk["chunk_id"] for chunk in chapter_chunks],
            ensure_ascii=False,
        ),
    }


def write_chunks_outputs(
    chunks: list[dict[str, Any]],
    chapter_index: list[dict[str, Any]],
    output_dir: str | Path = "data/processed",
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / "final_chunks.jsonl"
    json_path = output_dir / "final_chunks.json"
    csv_path = output_dir / "chapter_index.csv"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
        f.write("\n")

    fieldnames = [
        "chapter_number",
        "chapter_id",
        "kanda",
        "kanda_order",
        "chapter_title",
        "sarga_range",
        "source_pdf_pages",
        "printed_page_numbers",
        "question_count",
        "chunk_count",
        "chunk_ids",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(chapter_index)


def load_normalized_chapters(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        chapters = json.load(f)
    if not isinstance(chapters, list):
        raise ValueError(f"{path} must contain a JSON array of normalized chapters.")
    return chapters


def build_chunks_file(
    input_path: str | Path = "data/intermediate/chapters_english_normalized.json",
    output_dir: str | Path = "data/processed",
    translation_model: str = DEFAULT_TRANSLATION_MODEL,
) -> ChunkBuildResult:
    chapters = load_normalized_chapters(input_path)
    result = build_chunks_from_chapters(chapters, translation_model=translation_model)
    write_chunks_outputs(result.chunks, result.chapter_index, output_dir=output_dir)
    return result


def chunk_counts_by_type(chunks: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(chunk["metadata"]["chunk_type"] for chunk in chunks))


def _format_list(label: str, values: list[Any]) -> str:
    if not values:
        return f"{label}: None listed"
    return f"{label}: {', '.join(str(value) for value in values)}"
