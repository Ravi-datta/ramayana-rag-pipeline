from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ramayana_rag.entities.alias_loader import AliasEntry, load_entity_aliases


COMMON_CANDIDATES = {
    "At",
    "Bala Kanda",
    "Chapter",
    "First Chapter",
    "Kanda",
    "King",
    "Lord",
    "Maharaja",
    "Maharshi",
    "Ramayana",
    "River",
    "Sri",
    "The",
    "This",
}

CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z])(?:[A-Z][A-Za-z]+(?:'s)?)(?:\s+[A-Z][A-Za-z]+(?:'s)?)*(?![A-Za-z])"
)


@dataclass(frozen=True)
class NormalizationResult:
    chapters: list[dict[str, Any]]
    audit: dict[str, Any]


class EntityResolver:
    def __init__(self, aliases: Iterable[AliasEntry]) -> None:
        self.aliases = list(aliases)
        self.known_terms = {
            entry.alias.casefold()
            for entry in self.aliases
            if entry.match_type == "english_case_insensitive"
        }
        self.known_terms.update(entry.canonical.casefold() for entry in self.aliases)

    @classmethod
    def from_yaml(cls, path: str | Path = "configs/entity_aliases.yaml") -> "EntityResolver":
        return cls(load_entity_aliases(path))

    def normalize_chapters(self, chapters: list[dict[str, Any]]) -> NormalizationResult:
        normalized: list[dict[str, Any]] = []
        audit_chapters: list[dict[str, Any]] = []

        for chapter in chapters:
            normalized_chapter, audit_record = self.normalize_chapter(chapter)
            normalized.append(normalized_chapter)
            audit_chapters.append(audit_record)

        audit = {
            "chapter_count": len(normalized),
            "total_entity_mentions": sum(
                len(chapter.get("entity_mentions", [])) for chapter in normalized
            ),
            "total_unmapped_entity_candidates": sum(
                len(chapter.get("unmapped_entity_candidates", [])) for chapter in normalized
            ),
            "chapters": audit_chapters,
        }

        return NormalizationResult(chapters=normalized, audit=audit)

    def normalize_chapter(self, chapter: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        normalized = copy.deepcopy(chapter)
        chapter_field_mentions = self.find_mentions(self._chapter_content_text_fields(normalized))
        note_mentions = self.find_mentions(self._translation_note_text_fields(normalized))
        all_mentions = list(chapter_field_mentions)

        for question in normalized.get("questions", []):
            question_mentions = self.find_mentions(self._question_entity_mention_text_fields(question))
            key_mentions = self.find_mentions(self._question_key_entity_text_fields(question))
            question["entity_mentions"] = question_mentions
            question["key_entities"] = self._canonical_names(key_mentions, include_places=True)
            all_mentions.extend(
                {
                    **mention,
                    "field": f"questions[{question.get('question_number')}].{mention['field']}",
                }
                for mention in question_mentions
            )

        normalized["entity_mentions"] = self._dedupe_mentions(all_mentions)
        normalized["note_entity_mentions"] = note_mentions
        normalized["canonical_entities"] = self._canonical_names(
            normalized["entity_mentions"],
            include_places=False,
        )
        normalized["places"] = self._place_names(normalized["entity_mentions"])
        normalized["unmapped_entity_candidates"] = self.find_unmapped_candidates(normalized)

        audit_record = {
            "chapter_number": normalized.get("chapter_number"),
            "chapter_id": normalized.get("chapter_id"),
            "entity_mentions": len(normalized["entity_mentions"]),
            "note_entity_mentions": len(normalized["note_entity_mentions"]),
            "canonical_entities": normalized["canonical_entities"],
            "places": normalized["places"],
            "unmapped_entity_candidates": normalized["unmapped_entity_candidates"],
        }

        return normalized, audit_record

    def find_mentions(self, fields: Iterable[tuple[str, str]]) -> list[dict[str, str]]:
        mentions: list[dict[str, str]] = []

        for field, text in fields:
            if not text:
                continue

            field_mentions: list[dict[str, Any]] = []
            occupied_spans: list[tuple[int, int]] = []

            for entry in self.aliases:
                for start, end, matched_text in self._iter_matches(entry, text):
                    if self._overlaps((start, end), occupied_spans):
                        continue

                    occupied_spans.append((start, end))
                    field_mentions.append(
                        {
                            "alias": matched_text,
                            "canonical": entry.canonical,
                            "field": field,
                            "category": entry.category,
                            "match_type": entry.match_type,
                            "_start": start,
                        }
                    )

            field_mentions.sort(key=lambda mention: mention["_start"])
            for mention in field_mentions:
                mention.pop("_start", None)
                mentions.append(mention)

        return self._dedupe_mentions(mentions)

    def find_unmapped_candidates(self, chapter: dict[str, Any]) -> list[str]:
        candidates: list[str] = []
        seen: set[str] = set()

        for _field, text in self._all_text_fields(chapter):
            if not text:
                continue
            for match in CANDIDATE_RE.finditer(text):
                candidate = match.group(0).strip()
                if self._is_mapped_or_common_candidate(candidate):
                    continue

                key = candidate.casefold()
                if key not in seen:
                    seen.add(key)
                    candidates.append(candidate)

        return candidates

    def _iter_matches(self, entry: AliasEntry, text: str) -> Iterable[tuple[int, int, str]]:
        if entry.match_type == "english_case_insensitive":
            if entry.pattern is None:
                return
            for match in entry.pattern.finditer(text):
                yield match.start(), match.end(), match.group(0)
            return

        start = 0
        while True:
            idx = text.find(entry.alias, start)
            if idx == -1:
                break
            yield idx, idx + len(entry.alias), entry.alias
            start = idx + len(entry.alias)

    @staticmethod
    def _overlaps(span: tuple[int, int], occupied_spans: list[tuple[int, int]]) -> bool:
        start, end = span
        return any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied_spans)

    @staticmethod
    def _dedupe_mentions(mentions: Iterable[dict[str, str]]) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen: set[tuple[str, str, str, str, str]] = set()

        for mention in mentions:
            key = (
                mention["alias"].casefold(),
                mention["canonical"],
                mention["field"],
                mention["category"],
                mention["match_type"],
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(mention)

        return deduped

    @staticmethod
    def _canonical_names(
        mentions: Iterable[dict[str, str]],
        include_places: bool,
    ) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for mention in mentions:
            if not include_places and mention["category"] == "place":
                continue

            canonical = mention["canonical"]
            if canonical not in seen:
                seen.add(canonical)
                names.append(canonical)

        return names

    @staticmethod
    def _place_names(mentions: Iterable[dict[str, str]]) -> list[str]:
        places: list[str] = []
        seen: set[str] = set()

        for mention in mentions:
            if mention["category"] != "place":
                continue

            canonical = mention["canonical"]
            if canonical not in seen:
                seen.add(canonical)
                places.append(canonical)

        return places

    @staticmethod
    def _chapter_content_text_fields(chapter: dict[str, Any]) -> list[tuple[str, str]]:
        fields = [
            ("chapter_title", chapter.get("chapter_title", "")),
            ("chapter_summary", chapter.get("chapter_summary", "")),
        ]
        return [(field, text) for field, text in fields if isinstance(text, str)]

    @staticmethod
    def _translation_note_text_fields(chapter: dict[str, Any]) -> list[tuple[str, str]]:
        fields = [
            (f"translation_notes[{idx}]", note)
            for idx, note in enumerate(chapter.get("translation_notes", []))
        ]
        return [(field, text) for field, text in fields if isinstance(text, str)]

    @staticmethod
    def _question_entity_mention_text_fields(question: dict[str, Any]) -> list[tuple[str, str]]:
        fields = [
            ("question", question.get("question", "")),
            ("correct_answer", question.get("correct_answer", "")),
            ("answer", question.get("answer", "")),
        ]

        for option in question.get("options", []):
            if isinstance(option, dict):
                label = option.get("label", "")
                fields.append((f"options[{label}].text", option.get("text", "")))

        return [(field, text) for field, text in fields if isinstance(text, str)]

    @staticmethod
    def _question_key_entity_text_fields(question: dict[str, Any]) -> list[tuple[str, str]]:
        fields = [("question", question.get("question", ""))]
        answer_type = question.get("answer_type")

        if answer_type == "multiple_choice":
            fields.append(("correct_answer", question.get("correct_answer", "")))
        else:
            fields.extend(
                [
                    ("correct_answer", question.get("correct_answer", "")),
                    ("answer", question.get("answer", "")),
                ]
            )

        return [(field, text) for field, text in fields if isinstance(text, str)]

    def _all_text_fields(self, chapter: dict[str, Any]) -> list[tuple[str, str]]:
        fields = self._chapter_content_text_fields(chapter)
        for question in chapter.get("questions", []):
            fields.extend(
                (f"questions[{question.get('question_number')}].{field}", text)
                for field, text in self._question_entity_mention_text_fields(question)
            )
        return fields

    def _is_mapped_or_common_candidate(self, candidate: str) -> bool:
        if candidate in COMMON_CANDIDATES:
            return True

        if candidate.casefold() in self.known_terms:
            return True

        words = candidate.split()
        if words and words[0] in COMMON_CANDIDATES:
            return True

        return False


def normalize_entities_file(
    input_path: str | Path = "data/intermediate/chapters_english.json",
    output_path: str | Path = "data/intermediate/chapters_english_normalized.json",
    aliases_path: str | Path = "configs/entity_aliases.yaml",
    audit_output_path: str | Path | None = "data/intermediate/entity_normalization_audit.json",
) -> NormalizationResult:
    input_path = Path(input_path)
    output_path = Path(output_path)

    with input_path.open("r", encoding="utf-8") as f:
        chapters = json.load(f)

    if not isinstance(chapters, list):
        raise ValueError(f"{input_path} must contain a JSON array of translated chapters.")

    resolver = EntityResolver.from_yaml(aliases_path)
    result = resolver.normalize_chapters(chapters)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result.chapters, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if audit_output_path:
        audit_path = Path(audit_output_path)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("w", encoding="utf-8") as f:
            json.dump(result.audit, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return result
