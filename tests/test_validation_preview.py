from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.validation.reports import build_markdown_preview, write_validation_report


class ValidationPreviewSmokeTest(unittest.TestCase):
    def test_report_and_preview_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            intermediate = root / "intermediate"
            processed = root / "processed"
            intermediate.mkdir()
            processed.mkdir()

            telugu_chapters = [
                {"chapter_number": 1, "questions": [{"question_number": number} for number in range(1, 6)]}
            ]
            normalized_chapters = [
                {
                    "chapter_number": 1,
                    "chapter_id": "bala_001",
                    "kanda": "Bala Kanda",
                    "kanda_order": 1,
                    "sarga_range": "1-6",
                    "chapter_title": "First Chapter",
                    "chapter_summary": "A short summary.",
                    "questions": [
                        {
                            "question_number": 1,
                            "question": "Who composed the Ramayana?",
                            "answer_type": "direct_answer",
                            "options": [],
                            "correct_answer": "Valmiki",
                            "answer": "Valmiki",
                            "key_entities": ["Valmiki"],
                            "entity_mentions": [],
                        }
                    ],
                    "canonical_entities": ["Valmiki"],
                    "entity_mentions": [],
                    "places": ["Ayodhya"],
                    "themes": ["composition"],
                    "source_pdf_pages": [7],
                    "printed_page_numbers": ["11"],
                    "unmapped_entity_candidates": [],
                }
            ]
            chunks = [
                {
                    "chunk_id": "ramayana_bala_001_summary",
                    "text": "Summary text",
                    "metadata": {
                        "document_title": "Sri Ramayanamu - Prashnavali",
                        "source_file": "ramayana.pdf",
                        "language_original": "Telugu",
                        "language_output": "English",
                        "kanda": "Bala Kanda",
                        "kanda_order": 1,
                        "chapter_number": 1,
                        "chapter_title": "First Chapter",
                        "sarga_range": "1-6",
                        "question_number": None,
                        "chunk_type": "chapter_summary",
                        "answer_type": None,
                        "canonical_entities": ["Valmiki"],
                        "entity_mentions": [],
                        "places": ["Ayodhya"],
                        "themes": ["composition"],
                        "source_pdf_pages": [7],
                        "printed_page_numbers": ["11"],
                        "translation_model": "deepseek-chat",
                        "pipeline_version": "1.0.0",
                    },
                }
            ]

            (intermediate / "chapters_telugu.json").write_text(
                json.dumps(telugu_chapters),
                encoding="utf-8",
            )
            (intermediate / "chapters_english_normalized.json").write_text(
                json.dumps(normalized_chapters),
                encoding="utf-8",
            )
            (processed / "final_chunks.json").write_text(json.dumps(chunks), encoding="utf-8")
            (processed / "final_chunks.jsonl").write_text(
                "\n".join(json.dumps(chunk) for chunk in chunks) + "\n",
                encoding="utf-8",
            )
            (processed / "chapter_index.csv").write_text(
                "chapter_number,chapter_id,kanda,kanda_order,chapter_title,sarga_range,"
                "source_pdf_pages,printed_page_numbers,question_count,chunk_count,chunk_ids\n",
                encoding="utf-8",
            )

            report_path = processed / "validation_report.json"
            preview_path = processed / "final_chunks_preview.md"
            report = write_validation_report(
                output_path=report_path,
                chapters_telugu_path=intermediate / "chapters_telugu.json",
                normalized_chapters_path=intermediate / "chapters_english_normalized.json",
                chunks_json_path=processed / "final_chunks.json",
                chunks_jsonl_path=processed / "final_chunks.jsonl",
                chapter_index_path=processed / "chapter_index.csv",
            )
            preview = build_markdown_preview(
                normalized_chapters_path=intermediate / "chapters_english_normalized.json",
                validation_report_path=report_path,
                output_path=preview_path,
            )

            self.assertTrue(report_path.exists())
            self.assertTrue(preview_path.exists())
            self.assertIn("parsing", report)
            self.assertIn("translation", report)
            self.assertIn("chunking", report)
            self.assertIn("entity_normalization", report)
            self.assertGreater(len(preview), 0)


if __name__ == "__main__":
    unittest.main()
