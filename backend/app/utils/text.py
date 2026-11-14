from __future__ import annotations

import json
import re
from typing import Any

WHITESPACE = re.compile(r"[ \t\u00a0]+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“])|\n{2,}")
DEFAULT_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was",
    "were", "be", "been", "it", "this", "that", "what", "who", "when", "where", "how", "which",
    "all", "any", "from", "at", "by", "as", "about", "into", "show", "find", "me", "please",
    "there", "their", "they", "has", "have", "had", "do", "does", "did", "can", "could", "would",
    "should", "between", "incident", "evidence", "happened", "happens",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [WHITESPACE.sub(" ", line).strip() for line in value.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def truncate(value: str, limit: int = 2000, suffix: str = "…") -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - len(suffix))].rstrip() + suffix


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for block in SENTENCE_SPLIT.split(clean_text(text)):
        block = block.strip()
        if len(block) >= 3:
            sentences.append(block)
    return sentences


def excerpt_around(text: str, needle: str, radius: int = 140) -> str:
    if not needle:
        return truncate(text, radius * 2)
    index = text.lower().find(needle.lower())
    if index < 0:
        return truncate(text, radius * 2)
    start = max(0, index - radius)
    end = min(len(text), index + len(needle) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def tokenize(value: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9@._+-]{2,}", value.lower())
    return [t for t in tokens if t not in DEFAULT_STOPWORDS]


def slugify(value: str, limit: int = 60) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:limit] or "item"


def safe_json(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))
