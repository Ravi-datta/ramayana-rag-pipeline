from __future__ import annotations

import re
from typing import Any


QUESTION_START_RE = re.compile(
    r"(?m)(?:^|\n)\s*(?P<num>[1-5])\s*(?:వ)?\s*[\.\)]?\s*(?:ప్రశ్న|పశ్న)\s*(?::)?"
)

UNNUMBERED_QUESTION_RE = re.compile(
    r"(?m)(?:^|\n)\s*(?:ప్రశ్న|పశ్న)\s*(?::)?"
)

ANSWER_LABEL_RE = re.compile(r"జవాబు\s*(?::)?", re.MULTILINE)
ANSWER_KEY_HEADER_RE = re.compile(r"జవాబులు\s*(?::)?", re.MULTILINE)

OPTION_START_RE = re.compile(r"(?<!\d)(?P<label>[1-4])\s*[\.\)]\s*")

FALLBACK_ANSWER_KEY_RE = re.compile(
    r"(?ms)\n\s*[^\n]*అధ్యాయము\s*\n\s*"
    r"1\s*\.\s*[1-4]\s*\..*?"
    r"2\s*\.\s*[1-4]\s*\..*?"
    r"3\s*\.",
)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*:\s*", ": ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def promote_unnumbered_first_question(text: str) -> str:
    numbered_matches = list(QUESTION_START_RE.finditer(text))

    if not numbered_matches:
        return text

    first_numbered = numbered_matches[0]
    first_number = int(first_numbered.group("num"))

    if first_number == 1:
        return text

    if first_number != 2:
        return text

    prefix = text[: first_numbered.start()]
    unnumbered_matches = list(UNNUMBERED_QUESTION_RE.finditer(prefix))

    if not unnumbered_matches:
        return text

    marker = unnumbered_matches[-1]
    return text[: marker.start()] + "\n1. ప్రశ్న" + text[marker.end() :]


def split_answer_key_section_after_questions(text: str, first_question_pos: int) -> tuple[str, str]:
    answer_key_matches = [
        match
        for match in ANSWER_KEY_HEADER_RE.finditer(text)
        if match.start() > first_question_pos
    ]

    if answer_key_matches:
        match = answer_key_matches[-1]
        return text[: match.start()].strip(), text[match.start() :].strip()

    fallback_matches = [
        match
        for match in FALLBACK_ANSWER_KEY_RE.finditer(text)
        if match.start() > first_question_pos
    ]

    if fallback_matches:
        match = fallback_matches[-1]
        return text[: match.start()].strip(), text[match.start() :].strip()

    return text, ""


def parse_answer_keys(answer_key_text: str) -> dict[int, str]:
    keys: dict[int, str] = {}

    if not answer_key_text:
        return keys

    cleaned = answer_key_text
    cleaned = cleaned.replace("జవాబులు", " ")
    cleaned = re.sub(r"^[^\n]*అధ్యాయము", " ", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace(":", " ")
    cleaned = normalize_text(cleaned)

    pattern = re.compile(
        r"(?P<qnum>[1-5])\s*\.\s*"
        r"(?:(?P<option>[1-4])\s*\.\s*)?"
        r"(?P<answer>.*?)(?=(?:\s+[1-5]\s*\.)|$)",
        re.DOTALL,
    )

    for match in pattern.finditer(cleaned):
        qnum = int(match.group("qnum"))
        option = match.group("option")
        answer = normalize_text(match.group("answer"))

        if not answer:
            continue

        if option:
            keys[qnum] = f"{option}. {answer}"
        else:
            keys[qnum] = answer

    return keys


def parse_options(answer_text: str) -> list[dict[str, str]]:
    flat = " ".join(line.strip() for line in answer_text.splitlines() if line.strip())
    matches = list(OPTION_START_RE.finditer(flat))

    if len(matches) < 2:
        return []

    options: list[dict[str, str]] = []

    for idx, match in enumerate(matches):
        label = match.group("label")
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(flat)
        option_text = normalize_text(flat[start:end])

        if option_text:
            options.append({"label": label, "text": option_text})

    labels = [option["label"] for option in options]

    if labels[:2] != ["1", "2"]:
        return []

    return options


def split_question_and_options_without_answer_label(block: str) -> tuple[str, str]:
    option_matches = list(OPTION_START_RE.finditer(block))

    if len(option_matches) < 2:
        return block, ""

    labels = [match.group("label") for match in option_matches[:2]]

    if labels != ["1", "2"]:
        return block, ""

    first_option = option_matches[0]
    question_text = block[: first_option.start()]
    answer_text = block[first_option.start() :]

    return question_text, answer_text


def infer_answer_type(question_number: int, options: list[dict[str, str]]) -> str:
    if options:
        return "multiple_choice"

    if question_number == 3:
        return "direct_answer"

    return "narrative"


def strip_question_prefix(block: str) -> str:
    return QUESTION_START_RE.sub("", block, count=1).strip(" :\n\t")


def parse_question_block(question_number: int, block: str, answer_keys: dict[int, str]) -> dict[str, Any]:
    block = normalize_text(block)
    answer_match = ANSWER_LABEL_RE.search(block)

    if answer_match:
        question_text = block[: answer_match.start()]
        answer_text = block[answer_match.end() :]
    else:
        stripped_block = strip_question_prefix(block)
        question_text, answer_text = split_question_and_options_without_answer_label(stripped_block)

    question_text = normalize_text(strip_question_prefix(question_text))
    answer_text = normalize_text(answer_text)

    options = parse_options(answer_text)
    answer_type = infer_answer_type(question_number, options)

    if answer_type == "multiple_choice":
        answer_key_telugu = answer_keys.get(question_number)
        answer_telugu = None
    elif answer_type == "direct_answer":
        answer_key_telugu = answer_keys.get(question_number)
        answer_telugu = answer_key_telugu
    else:
        answer_key_telugu = None
        answer_telugu = answer_text

    warnings: list[str] = []

    if not question_text:
        warnings.append("Empty question text.")

    if answer_type == "multiple_choice" and len(options) < 4:
        warnings.append(f"Expected 4 options, detected {len(options)}.")

    if answer_type in {"multiple_choice", "direct_answer"} and not answer_key_telugu:
        warnings.append("Missing answer key.")

    if answer_type == "narrative" and not answer_telugu:
        warnings.append("Missing narrative answer.")

    return {
        "question_number": question_number,
        "question_telugu": question_text,
        "answer_type": answer_type,
        "options_telugu": options,
        "answer_key_telugu": answer_key_telugu,
        "answer_telugu": answer_telugu,
        "parser_warnings": warnings,
    }


def parse_questions_from_chapter_text(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    parser_warnings: list[str] = []

    text = normalize_text(text)
    text = promote_unnumbered_first_question(text)

    initial_matches = list(QUESTION_START_RE.finditer(text))
    if not initial_matches:
        return [], ["No question starts detected."]

    first_question_pos = initial_matches[0].start()

    text = text[first_question_pos:]
    text = promote_unnumbered_first_question(text)

    matches_after_trim = list(QUESTION_START_RE.finditer(text))
    if not matches_after_trim:
        return [], ["No question starts detected."]

    first_question_pos = matches_after_trim[0].start()

    main_text, answer_key_text = split_answer_key_section_after_questions(
        text=text,
        first_question_pos=first_question_pos,
    )

    answer_keys = parse_answer_keys(answer_key_text)
    matches = list(QUESTION_START_RE.finditer(main_text))

    if not matches:
        return [], ["No question starts detected."]

    questions: list[dict[str, Any]] = []

    for idx, match in enumerate(matches):
        question_number = int(match.group("num"))
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(main_text)
        block = main_text[start:end].strip()

        parsed = parse_question_block(question_number, block, answer_keys)
        questions.append(parsed)

    deduped: dict[int, dict[str, Any]] = {}
    for question in questions:
        deduped.setdefault(question["question_number"], question)

    questions = [deduped[num] for num in sorted(deduped)]

    detected_numbers = [question["question_number"] for question in questions]

    if len(questions) != 5:
        parser_warnings.append(f"Expected 5 questions, detected {len(questions)}.")

    missing = [num for num in range(1, 6) if num not in set(detected_numbers)]
    if missing:
        parser_warnings.append(f"Missing question numbers: {missing}")

    for question in questions:
        for warning in question.get("parser_warnings", []):
            parser_warnings.append(f"Q{question['question_number']}: {warning}")

    return questions, parser_warnings


def attach_questions_to_chapters(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []

    for chapter in chapters:
        questions, warnings = parse_questions_from_chapter_text(chapter["raw_telugu_text"])

        prior_warnings = [
            warning
            for warning in chapter.get("parser_warnings", [])
            if not warning.startswith("Expected 5 questions")
            and not warning.startswith("Missing question numbers")
            and not warning.startswith("No question starts")
            and not warning.startswith("Q")
        ]

        chapter_warnings = prior_warnings + warnings

        updated_chapter = {
            **chapter,
            "questions": questions,
            "parser_warnings": chapter_warnings,
            "needs_review": bool(chapter_warnings),
        }

        updated.append(updated_chapter)

    return updated
