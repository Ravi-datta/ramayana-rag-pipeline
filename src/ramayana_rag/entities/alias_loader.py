from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ALLOWED_CATEGORIES = {
    "primary",
    "sage",
    "deity",
    "rakshasa",
    "vanara",
    "supporting",
    "place",
}


@dataclass(frozen=True)
class AliasEntry:
    canonical: str
    alias: str
    category: str
    match_type: str
    pattern: re.Pattern[str] | None = None


def normalize_alias_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_ascii_text(text: str) -> bool:
    return all(ord(char) < 128 for char in text)


def compile_english_alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias)
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z]){escaped}(?![A-Za-z])", re.IGNORECASE)


def load_entity_aliases(path: str | Path = "configs/entity_aliases.yaml") -> list[AliasEntry]:
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    entities = raw.get("entities")
    if not isinstance(entities, dict):
        raise ValueError(f"{path} must contain an 'entities' mapping.")

    entries: list[AliasEntry] = []

    for canonical, config in entities.items():
        if not isinstance(config, dict):
            raise ValueError(f"Entity config for {canonical!r} must be a mapping.")

        category = config.get("category")
        aliases = config.get("aliases")

        if category not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"Entity {canonical!r} has invalid category {category!r}. "
                f"Allowed: {sorted(ALLOWED_CATEGORIES)}"
            )

        if not isinstance(aliases, list) or not aliases:
            raise ValueError(f"Entity {canonical!r} must define a non-empty aliases list.")

        for alias in aliases:
            if not isinstance(alias, str):
                raise ValueError(f"Alias for {canonical!r} must be a string.")

            normalized_alias = normalize_alias_text(alias)
            if not normalized_alias:
                continue

            if is_ascii_text(normalized_alias):
                entries.append(
                    AliasEntry(
                        canonical=str(canonical),
                        alias=normalized_alias,
                        category=category,
                        match_type="english_case_insensitive",
                        pattern=compile_english_alias_pattern(normalized_alias),
                    )
                )
            else:
                entries.append(
                    AliasEntry(
                        canonical=str(canonical),
                        alias=normalized_alias,
                        category=category,
                        match_type="exact_substring",
                    )
                )

    return sorted(entries, key=lambda entry: len(entry.alias), reverse=True)


def load_entity_config(path: str | Path = "configs/entity_aliases.yaml") -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
