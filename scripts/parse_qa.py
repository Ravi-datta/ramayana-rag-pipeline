from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.parsing.chapter_parser import write_chapters_json
from ramayana_rag.parsing.qa_parser import attach_questions_to_chapters


def main() -> None:
    input_path = Path("data/intermediate/chapters_telugu.json")
    output_path = Path("data/intermediate/chapters_telugu.json")

    if not input_path.exists():
        raise FileNotFoundError(
            "Missing data/intermediate/chapters_telugu.json. Run scripts/parse_chapters.py first."
        )

    with input_path.open("r", encoding="utf-8") as f:
        chapters = json.load(f)

    chapters = attach_questions_to_chapters(chapters)
    write_chapters_json(chapters, output_path)

    total_questions = sum(len(chapter["questions"]) for chapter in chapters)

    question_count_issues = [
        {
            "chapter_number": chapter["chapter_number"],
            "question_count": len(chapter["questions"]),
            "warnings": chapter.get("parser_warnings", []),
        }
        for chapter in chapters
        if len(chapter["questions"]) != 5
    ]

    answer_type_counts = Counter(
        question["answer_type"]
        for chapter in chapters
        for question in chapter["questions"]
    )

    review_chapters = [
        chapter["chapter_number"]
        for chapter in chapters
        if chapter.get("needs_review")
    ]

    print(f"Chapters loaded: {len(chapters)}")
    print(f"Total questions detected: {total_questions}")
    print(f"Answer type counts: {dict(answer_type_counts)}")
    print(f"Chapters with question count issues: {question_count_issues}")
    print(f"Chapters needing review: {review_chapters}")

    print("\nChapter 1 question summary:")
    chapter_1 = chapters[0]
    for question in chapter_1["questions"]:
        print(
            {
                "question_number": question["question_number"],
                "answer_type": question["answer_type"],
                "options": len(question["options_telugu"]),
                "has_answer_key": bool(question["answer_key_telugu"]),
                "has_answer": bool(question["answer_telugu"]),
            }
        )


if __name__ == "__main__":
    main()
