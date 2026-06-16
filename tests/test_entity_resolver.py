from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ramayana_rag.entities.entity_resolver import EntityResolver


class EntityResolverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = EntityResolver.from_yaml(ROOT / "configs/entity_aliases.yaml")

    def test_required_alias_mappings_from_notes(self) -> None:
        text = (
            "Raghunandana stood with Saumitri and Janaki. "
            "Kaushika spoke while Dashakantha watched Vayuputra. "
            "Vibhishana and Indrajit went from Ayodhya to Lanka."
        )

        mentions = self.resolver.find_mentions([("sample", text)])
        mapping = {(mention["alias"], mention["canonical"]) for mention in mentions}
        categories = {mention["canonical"]: mention["category"] for mention in mentions}

        self.assertIn(("Raghunandana", "Rama"), mapping)
        self.assertIn(("Saumitri", "Lakshmana"), mapping)
        self.assertIn(("Janaki", "Sita"), mapping)
        self.assertIn(("Kaushika", "Vishvamitra"), mapping)
        self.assertIn(("Dashakantha", "Ravana"), mapping)
        self.assertIn(("Vayuputra", "Hanuman"), mapping)
        self.assertIn(("Vibhishana", "Vibhishana"), mapping)
        self.assertIn(("Indrajit", "Indrajit"), mapping)
        self.assertEqual(categories["Ayodhya"], "place")
        self.assertEqual(categories["Lanka"], "place")

    def test_visible_text_is_not_rewritten(self) -> None:
        chapter = {
            "chapter_number": 1,
            "chapter_id": "test_001",
            "chapter_title": "Raghunandana in Ayodhya",
            "chapter_summary": "Janaki speaks to Saumitri.",
            "canonical_entities": [],
            "places": [],
            "translation_notes": [],
            "questions": [
                {
                    "question_number": 1,
                    "question": "What did Vayuputra do in Lanka?",
                    "answer": "Vayuputra searched for Janaki.",
                    "correct_answer": "Vayuputra",
                    "options": [],
                    "key_entities": [],
                }
            ],
        }
        original = copy.deepcopy(chapter)

        normalized, _audit = self.resolver.normalize_chapter(chapter)

        self.assertEqual(normalized["chapter_title"], original["chapter_title"])
        self.assertEqual(normalized["chapter_summary"], original["chapter_summary"])
        self.assertEqual(normalized["questions"][0]["question"], original["questions"][0]["question"])
        self.assertEqual(normalized["questions"][0]["answer"], original["questions"][0]["answer"])
        self.assertIn("Rama", normalized["canonical_entities"])
        self.assertIn("Sita", normalized["canonical_entities"])
        self.assertIn("Lakshmana", normalized["canonical_entities"])
        self.assertIn("Hanuman", normalized["canonical_entities"])
        self.assertIn("Ayodhya", normalized["places"])
        self.assertIn("Lanka", normalized["places"])

    def test_translation_note_only_entity_is_not_promoted(self) -> None:
        chapter = {
            "chapter_number": 1,
            "chapter_id": "test_001",
            "chapter_title": "First Chapter",
            "chapter_summary": "Valmiki composes the Ramayana.",
            "canonical_entities": [],
            "places": [],
            "translation_notes": ["Sumantra appears only in this note."],
            "questions": [
                {
                    "question_number": 1,
                    "answer_type": "direct_answer",
                    "question": "Who composed the Ramayana?",
                    "answer": "Valmiki",
                    "correct_answer": "Valmiki",
                    "options": [],
                    "key_entities": [],
                }
            ],
        }

        normalized, _audit = self.resolver.normalize_chapter(chapter)

        self.assertIn("Valmiki", normalized["canonical_entities"])
        self.assertNotIn("Sumantra", normalized["canonical_entities"])
        self.assertFalse(
            any(mention["canonical"] == "Sumantra" for mention in normalized["entity_mentions"])
        )
        self.assertTrue(
            any(mention["canonical"] == "Sumantra" for mention in normalized["note_entity_mentions"])
        )

    def test_mcq_distractor_entities_are_not_key_entities(self) -> None:
        chapter = {
            "chapter_number": 1,
            "chapter_id": "test_001",
            "chapter_title": "First Chapter",
            "chapter_summary": "A question about creation.",
            "canonical_entities": [],
            "places": [],
            "translation_notes": [],
            "questions": [
                {
                    "question_number": 1,
                    "answer_type": "multiple_choice",
                    "question": "Whom did Narayana create first?",
                    "answer": "Brahma",
                    "correct_answer": "Brahma",
                    "options": [
                        {"label": "1", "text": "Sumantra"},
                        {"label": "2", "text": "Brahma"},
                        {"label": "3", "text": "Ravana"},
                        {"label": "4", "text": "Hanuman"},
                    ],
                    "key_entities": [],
                }
            ],
        }

        normalized, _audit = self.resolver.normalize_chapter(chapter)
        question = normalized["questions"][0]

        self.assertIn("Narayana", question["key_entities"])
        self.assertIn("Brahma", question["key_entities"])
        self.assertNotIn("Sumantra", question["key_entities"])
        self.assertNotIn("Ravana", question["key_entities"])
        self.assertNotIn("Hanuman", question["key_entities"])
        self.assertTrue(
            any(mention["canonical"] == "Sumantra" for mention in question["entity_mentions"])
        )
        self.assertTrue(
            any(mention["canonical"] == "Ravana" for mention in question["entity_mentions"])
        )
        self.assertTrue(
            any(mention["canonical"] == "Hanuman" for mention in question["entity_mentions"])
        )


if __name__ == "__main__":
    unittest.main()
