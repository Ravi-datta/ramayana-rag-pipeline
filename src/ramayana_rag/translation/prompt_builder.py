from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """You are a Telugu-to-English Ramayana translation engine.
Use only the provided Telugu chapter payload.
Return strict JSON only. Do not include markdown, comments, or explanatory text.
Translate faithfully without adding facts that are not supported by the source.
Preserve meaningful epithets in visible English text where useful.
Do not normalize entities to an external alias list; list obvious canonical names only from context.
"""


def build_chapter_translation_prompt(chapter: dict[str, Any]) -> tuple[str, str]:
    chapter_payload = {
        "chapter_number": chapter.get("chapter_number"),
        "chapter_id": chapter.get("chapter_id"),
        "kanda_telugu": chapter.get("kanda_telugu"),
        "kanda_english": chapter.get("kanda_english"),
        "kanda_order": chapter.get("kanda_order"),
        "sarga_range": chapter.get("sarga_range"),
        "chapter_title_telugu": chapter.get("chapter_title_telugu"),
        "source_pdf_pages": chapter.get("source_pdf_pages", []),
        "printed_page_numbers": chapter.get("printed_page_numbers", []),
        "questions": chapter.get("questions", []),
        "raw_telugu_text": chapter.get("raw_telugu_text", ""),
        "parser_warnings": chapter.get("parser_warnings", []),
        "needs_review": chapter.get("needs_review", False),
    }

    schema = {
        "chapter_number": "integer; same as input",
        "chapter_id": "string; same as input",
        "kanda": "English kanda name",
        "kanda_order": "integer; same as input",
        "sarga_range": "string or null; same as input",
        "chapter_title": "English translation of chapter_title_telugu",
        "chapter_summary": "concise English summary of the chapter context",
        "questions": [
            {
                "question_number": "integer; same as input question_number",
                "question": "English translation of question_telugu",
                "answer_type": "same as input answer_type",
                "options": [
                    {
                        "label": "same option label",
                        "text": "English translation of option text",
                    }
                ],
                "correct_answer": (
                    "English translation of answer_key_telugu for multiple_choice and "
                    "direct_answer; null if no answer key exists"
                ),
                "answer": (
                    "English translated answer. For multiple_choice, use the correct answer "
                    "text if known; otherwise null."
                ),
                "key_entities": ["canonical English entity names appearing in this QA"],
            }
        ],
        "canonical_entities": ["canonical English entity names found in the chapter"],
        "places": ["English place names found in the chapter"],
        "themes": ["short English theme labels supported by the chapter"],
        "translation_notes": [
            "brief notes for ambiguities, damaged text, uncertain names, or parser warnings"
        ],
        "source_pdf_pages": "same as input source_pdf_pages",
        "printed_page_numbers": "same as input printed_page_numbers",
    }

    user_prompt = (
        "Translate exactly one parsed Telugu chapter into English.\n"
        "Return one JSON object with this shape:\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        "Rules:\n"
        "- Do not omit any input question.\n"
        "- Keep question_number and answer_type unchanged.\n"
        "- Translate options into objects with label and text.\n"
        "- If source text is unclear or appears corrupted, translate as best as possible and "
        "record the uncertainty in translation_notes.\n"
        "- Return arrays for canonical_entities, places, themes, and translation_notes even "
        "when empty.\n"
        "- Return strict JSON only.\n\n"
        "Input chapter JSON:\n"
        f"{json.dumps(chapter_payload, ensure_ascii=False, indent=2)}"
    )

    return SYSTEM_PROMPT, user_prompt
