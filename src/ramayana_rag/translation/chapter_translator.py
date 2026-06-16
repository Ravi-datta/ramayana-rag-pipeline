from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ramayana_rag.translation.deepseek_client import DeepSeekClient
from ramayana_rag.translation.prompt_builder import build_chapter_translation_prompt


REQUIRED_CHAPTER_FIELDS = {
    "chapter_number",
    "chapter_id",
    "kanda",
    "kanda_order",
    "sarga_range",
    "chapter_title",
    "chapter_summary",
    "questions",
    "canonical_entities",
    "places",
    "themes",
    "translation_notes",
}

REQUIRED_QUESTION_FIELDS = {
    "question_number",
    "question",
    "answer_type",
    "options",
    "correct_answer",
    "answer",
    "key_entities",
}


class TranslationValidationError(RuntimeError):
    """Raised when translated chapter JSON does not match the required contract."""


class TranslationRunError(RuntimeError):
    """Raised after a run completes with one or more per-chapter failures."""


@dataclass(frozen=True)
class ChapterTranslationResult:
    translated_chapters: list[dict[str, Any]]
    audit_records: list[dict[str, Any]]
    failures: list[dict[str, Any]]


class ChapterTranslator:
    def __init__(
        self,
        input_path: str | Path = "data/intermediate/chapters_telugu.json",
        cache_dir: str | Path = "data/intermediate/translated_chapters",
        combined_output_path: str | Path = "data/intermediate/chapters_english.json",
        audit_output_path: str | Path = "data/intermediate/translation_audit.jsonl",
        client_factory: Callable[[], DeepSeekClient] | None = None,
    ) -> None:
        self.input_path = Path(input_path)
        self.cache_dir = Path(cache_dir)
        self.combined_output_path = Path(combined_output_path)
        self.audit_output_path = Path(audit_output_path)
        self.client_factory = client_factory or DeepSeekClient
        self._client: DeepSeekClient | None = None

    def translate(
        self,
        chapter_numbers: list[int] | None = None,
        force: bool = False,
    ) -> ChapterTranslationResult:
        chapters = self._load_chapters()
        selected = self._select_chapters(chapters, chapter_numbers)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.combined_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_output_path.parent.mkdir(parents=True, exist_ok=True)

        translated_chapters: list[dict[str, Any]] = []
        audit_records: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        with self.audit_output_path.open("w", encoding="utf-8") as audit_file:
            for chapter in selected:
                record = self._translate_one(chapter, force=force)
                translated_chapter = record.pop("translated_chapter", None)
                audit_records.append(record)
                audit_file.write(json.dumps(record, ensure_ascii=False) + "\n")

                if record["status"] in {"translated", "cached"}:
                    translated_chapters.append(translated_chapter)
                else:
                    failures.append(record)

        self._write_combined(translated_chapters)

        if failures:
            failed_numbers = ", ".join(str(item["chapter_number"]) for item in failures)
            raise TranslationRunError(f"Translation failed for chapter(s): {failed_numbers}")

        return ChapterTranslationResult(
            translated_chapters=translated_chapters,
            audit_records=audit_records,
            failures=failures,
        )

    def _translate_one(self, chapter: dict[str, Any], force: bool) -> dict[str, Any]:
        chapter_number = int(chapter["chapter_number"])
        cache_path = self.cache_path_for(chapter_number)
        started_at = time.perf_counter()

        base_record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "chapter_number": chapter_number,
            "chapter_id": chapter.get("chapter_id"),
            "cache_path": str(cache_path),
            "force": force,
        }

        if cache_path.exists() and not force:
            try:
                translated = self._read_json(cache_path)
                validate_translated_chapter(translated)
                return {
                    **base_record,
                    "status": "cached",
                    "attempts": 0,
                    "duration_seconds": round(time.perf_counter() - started_at, 3),
                    "translated_chapter": translated,
                }
            except Exception as exc:  # noqa: BLE001 - audit must capture cache validation errors.
                return {
                    **base_record,
                    "status": "failed",
                    "attempts": 0,
                    "duration_seconds": round(time.perf_counter() - started_at, 3),
                    "error_type": type(exc).__name__,
                    "error": f"Cached translation is invalid: {exc}",
                }

        try:
            system_prompt, user_prompt = build_chapter_translation_prompt(chapter)
            result = self._get_client().translate_json(system_prompt, user_prompt)
            translated = result.data
            validate_translated_chapter(translated)
            self._write_json(cache_path, translated)

            return {
                **base_record,
                "status": "translated",
                "attempts": result.attempts,
                "duration_seconds": round(time.perf_counter() - started_at, 3),
                "translated_chapter": translated,
            }
        except Exception as exc:  # noqa: BLE001 - continue to audit each requested chapter.
            return {
                **base_record,
                "status": "failed",
                "attempts": None,
                "duration_seconds": round(time.perf_counter() - started_at, 3),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    def _get_client(self) -> DeepSeekClient:
        if self._client is None:
            self._client = self.client_factory()
        return self._client

    def _load_chapters(self) -> list[dict[str, Any]]:
        if not self.input_path.exists():
            raise FileNotFoundError(f"Missing parsed Telugu chapters file: {self.input_path}")

        chapters = self._read_json(self.input_path)
        if not isinstance(chapters, list):
            raise ValueError(f"Expected {self.input_path} to contain a JSON array.")

        return chapters

    @staticmethod
    def _select_chapters(
        chapters: list[dict[str, Any]],
        chapter_numbers: list[int] | None,
    ) -> list[dict[str, Any]]:
        if not chapter_numbers:
            return chapters

        requested = list(dict.fromkeys(chapter_numbers))
        chapter_lookup = {int(chapter["chapter_number"]): chapter for chapter in chapters}
        missing = [number for number in requested if number not in chapter_lookup]

        if missing:
            raise ValueError(f"Requested chapter(s) not found: {missing}")

        return [chapter_lookup[number] for number in requested]

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    def _write_combined(self, translated_chapters: list[dict[str, Any]]) -> None:
        self._write_json(self.combined_output_path, translated_chapters)

    def cache_path_for(self, chapter_number: int) -> Path:
        return self.cache_dir / f"chapter_{chapter_number:03d}.json"


def validate_translated_chapter(chapter: dict[str, Any]) -> None:
    if not isinstance(chapter, dict):
        raise TranslationValidationError("Translated chapter must be a JSON object.")

    missing = sorted(REQUIRED_CHAPTER_FIELDS - set(chapter))
    if missing:
        raise TranslationValidationError(f"Translated chapter missing fields: {missing}")

    if not isinstance(chapter["questions"], list):
        raise TranslationValidationError("Translated chapter questions must be a list.")

    for field in ("canonical_entities", "places", "themes", "translation_notes"):
        if not isinstance(chapter[field], list):
            raise TranslationValidationError(f"Translated chapter field must be a list: {field}")

    for idx, question in enumerate(chapter["questions"], start=1):
        if not isinstance(question, dict):
            raise TranslationValidationError(f"Question {idx} must be a JSON object.")

        missing_question_fields = sorted(REQUIRED_QUESTION_FIELDS - set(question))
        if missing_question_fields:
            raise TranslationValidationError(
                f"Question {idx} missing fields: {missing_question_fields}"
            )

        if not isinstance(question["options"], list):
            raise TranslationValidationError(f"Question {idx} options must be a list.")

        if not isinstance(question["key_entities"], list):
            raise TranslationValidationError(f"Question {idx} key_entities must be a list.")
