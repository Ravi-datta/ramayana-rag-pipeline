from __future__ import annotations

import re


WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    return [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]


def split_text_by_word_limit(text: str, max_words: int) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []

    parts: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        sentence_words = count_words(sentence)

        if current and current_words + sentence_words > max_words:
            parts.append(" ".join(current).strip())
            current = []
            current_words = 0

        if sentence_words > max_words:
            words = sentence.split()
            for idx in range(0, len(words), max_words):
                chunk = " ".join(words[idx : idx + max_words]).strip()
                if chunk:
                    parts.append(chunk)
            continue

        current.append(sentence)
        current_words += sentence_words

    if current:
        parts.append(" ".join(current).strip())

    return parts
