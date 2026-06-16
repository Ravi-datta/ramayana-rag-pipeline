from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ramayana_rag.validation.quality_checks import build_validation_report, load_json


def write_validation_report(
    output_path: str | Path = "data/processed/validation_report.json",
    **paths: Any,
) -> dict[str, Any]:
    report = build_validation_report(**paths)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return report


def build_markdown_preview(
    normalized_chapters_path: str | Path = "data/intermediate/chapters_english_normalized.json",
    validation_report_path: str | Path = "data/processed/validation_report.json",
    output_path: str | Path = "data/processed/final_chunks_preview.md",
) -> str:
    chapters = load_json(normalized_chapters_path, default=[]) or []
    report = load_json(validation_report_path, default={}) or {}

    lines: list[str] = [
        "# Sri Ramayanamu - Prashnavali RAG Preview",
        "",
        "## Document Summary",
        "",
        "This preview summarizes the currently processed English, entity-normalized sample "
        "chapters and their question-answer content for reviewer inspection.",
        "",
        "## Validation Summary",
        "",
    ]

    parsing = report.get("parsing", {})
    translation = report.get("translation", {})
    chunking = report.get("chunking", {})
    entity_normalization = report.get("entity_normalization", {})

    lines.extend(
        [
            f"- Pipeline version: {report.get('pipeline_version', 'unknown')}",
            f"- Translation model: {report.get('translation_model', 'unknown')}",
            f"- Parsed chapters: {parsing.get('detected_chapters', 0)} / "
            f"{parsing.get('expected_chapters', 99)}",
            f"- Parsed questions: {parsing.get('detected_questions', 0)} / "
            f"{parsing.get('expected_questions', 495)}",
            f"- Translated/normalized chapters: {translation.get('translated_chapters', 0)}",
            f"- Total chunks: {chunking.get('total_chunks', 0)}",
            f"- Chunks with canonical entities: "
            f"{entity_normalization.get('chunks_with_canonical_entities', 0)}",
            "",
            "## Chunk Count Summary",
            "",
        ]
    )

    counts = chunking.get("chunk_counts_by_type", {})
    if counts:
        for chunk_type, count in sorted(counts.items()):
            lines.append(f"- {chunk_type}: {count}")
    else:
        lines.append("- No chunk counts available.")

    warnings = report.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)

    lines.extend(["", "## Processed Chapters", ""])

    for chapter in sorted(chapters, key=lambda item: int(item.get("chapter_number", 0))):
        lines.extend(render_chapter_preview(chapter))

    markdown = "\n".join(lines).rstrip() + "\n"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def render_chapter_preview(chapter: dict[str, Any]) -> list[str]:
    lines = [
        f"### Chapter {chapter.get('chapter_number')}: {chapter.get('chapter_title')}",
        "",
        f"- Kanda: {chapter.get('kanda')}",
        f"- Sarga range: {chapter.get('sarga_range')}",
        f"- Source PDF pages: {_format_list(chapter.get('source_pdf_pages', []))}",
        f"- Printed page numbers: {_format_list(chapter.get('printed_page_numbers', []))}",
        f"- Key entities: {_format_list(chapter.get('canonical_entities', []))}",
        f"- Places: {_format_list(chapter.get('places', []))}",
        "",
        f"**Summary:** {chapter.get('chapter_summary', '')}",
        "",
    ]

    for question in sorted(
        chapter.get("questions", []),
        key=lambda item: int(item.get("question_number", 0)),
    ):
        lines.extend(render_question_preview(question))

    return lines


def render_question_preview(question: dict[str, Any]) -> list[str]:
    question_number = question.get("question_number")
    lines = [
        f"#### Q{question_number}",
        "",
        f"**Question:** {question.get('question', '')}",
        "",
    ]

    if question.get("answer_type") == "multiple_choice":
        lines.append("**Options:**")
        for option in question.get("options", []):
            if isinstance(option, dict):
                lines.append(f"- {option.get('label')}. {option.get('text')}")
        lines.extend(
            [
                "",
                f"**Correct answer:** {question.get('correct_answer') or question.get('answer') or ''}",
            ]
        )
    else:
        lines.append(f"**Answer:** {question.get('answer') or question.get('correct_answer') or ''}")

    lines.extend(
        [
            "",
            f"**Key entities:** {_format_list(question.get('key_entities', []))}",
            "",
        ]
    )
    return lines


def _format_list(values: list[Any]) -> str:
    if not values:
        return "None listed"
    return ", ".join(str(value) for value in values)
