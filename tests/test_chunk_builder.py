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

from ramayana_rag.chunking.chunk_builder import build_chunks_file


class ChunkBuilderSmokeTest(unittest.TestCase):
    def test_chunks_are_self_contained_and_outputs_match(self) -> None:
        chapter = {
            "chapter_number": 1,
            "chapter_id": "bala_001",
            "kanda": "Bala Kanda",
            "kanda_order": 1,
            "sarga_range": "1-6",
            "chapter_title": "First Chapter",
            "chapter_summary": "Valmiki composes the Ramayana.",
            "canonical_entities": ["Valmiki", "Rama"],
            "entity_mentions": [],
            "places": ["Ayodhya"],
            "themes": ["composition"],
            "source_pdf_pages": [7, 8],
            "printed_page_numbers": ["11", "12"],
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
                },
                {
                    "question_number": 2,
                    "question": "Which city is described?",
                    "answer_type": "multiple_choice",
                    "options": [
                        {"label": "1", "text": "Ayodhya"},
                        {"label": "2", "text": "Lanka"},
                    ],
                    "correct_answer": "Ayodhya",
                    "answer": "Ayodhya",
                    "key_entities": ["Ayodhya"],
                    "entity_mentions": [],
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "chapters.json"
            output_dir = tmp_path / "processed"
            input_path.write_text(json.dumps([chapter]), encoding="utf-8")

            result = build_chunks_file(input_path=input_path, output_dir=output_dir)

            self.assertTrue(result.chunks)
            for chunk in result.chunks:
                self.assertTrue(chunk.get("chunk_id"))
                self.assertTrue(chunk.get("text"))
                self.assertIsInstance(chunk.get("metadata"), dict)
                metadata = chunk["metadata"]
                self.assertIn("chapter_number", metadata)
                self.assertIn("kanda", metadata)
                self.assertIn("chunk_type", metadata)

                if metadata["chunk_type"].startswith("qa_"):
                    question = next(
                        q
                        for q in chapter["questions"]
                        if q["question_number"] == metadata["question_number"]
                    )
                    self.assertIn(question["question"], chunk["text"])
                    self.assertTrue(
                        (question["answer"] and question["answer"] in chunk["text"])
                        or (
                            question["correct_answer"]
                            and question["correct_answer"] in chunk["text"]
                        )
                    )

            json_chunks = json.loads((output_dir / "final_chunks.json").read_text(encoding="utf-8"))
            jsonl_lines = [
                line
                for line in (output_dir / "final_chunks.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(json_chunks), len(jsonl_lines))
            self.assertEqual(len(result.chunks), len(json_chunks))
            self.assertTrue((output_dir / "chapter_index.csv").exists())


if __name__ == "__main__":
    unittest.main()
