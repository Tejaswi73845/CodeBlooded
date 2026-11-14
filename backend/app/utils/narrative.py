"""Cleanup for AI-generated narrative text shown next to already-rendered metadata."""

from __future__ import annotations

import re

from app.utils.text import clean_text

HEADER_FRAGMENT = re.compile(
    r"(?i)\b(?:message-id|reply-to|mime-version|content-type|attachments|x-[a-z0-9-]+)\b"
    r"\s*:?\s*(?:<[^<>]*>|\S+)"
)
ANGLE_ADDRESS = re.compile(r"<\s*[^<>@\s]+@[^<>\s]+\s*>")
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
WHITESPACE = re.compile(r"\s+")
CLAUSE_SPLIT = re.compile(r",\s+|;\s+|\s+[—–]\s+")
TIME_HINT = re.compile(
    r"(?i)\b("
    r"\d{1,2}:\d{2}(?::\d{2})?"
    r"|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?"
    r")\b"
)
TIME_LEAD = re.compile(r"(?i)^\s*(?:on|at|by|dated|around|in)\b")


def trim_restated_time(summary: str, occurred_at_raw: str | None = None) -> str:
    """Drop a leading date/time clause that merely repeats the card's own metadata."""
    text = clean_text(summary)
    if len(text) < 40:
        return text

    parts = CLAUSE_SPLIT.split(text, maxsplit=1)
    if len(parts) < 2:
        return text
    head, tail = parts[0].strip(), parts[1].strip()
    if not head or not tail:
        return text
    if len(head.split()) > 14 or not TIME_HINT.search(head):
        return text

    # Only trim when the clause refers to the same date the card already shows.
    if occurred_at_raw:
        digits = set(re.findall(r"\d{1,4}", occurred_at_raw))
        if not digits.intersection(re.findall(r"\d{1,4}", head)):
            return text
    elif not TIME_LEAD.search(head):
        return text

    if len(tail) < 40 or not tail[:1].isupper():
        return text
    return tail


def strip_header_syntax(text: str) -> str:
    """Remove header fields, Message-IDs, angle-bracket addresses and bare IPs."""
    cleaned = HEADER_FRAGMENT.sub("", clean_text(text))
    cleaned = ANGLE_ADDRESS.sub("", cleaned)
    cleaned = IPV4.sub("", cleaned)
    cleaned = WHITESPACE.sub(" ", cleaned)
    cleaned = re.sub(r"\b(?:and|with|or)\s+([.,;:])", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = cleaned.strip().lstrip(" ,;:-")
    if cleaned and cleaned[-1] in ",;:-":
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def sanitize_summary(summary: str, occurred_at_raw: str | None = None) -> str:
    """Remove header syntax and repeated time/location from a generated summary."""
    return trim_restated_time(strip_header_syntax(summary), occurred_at_raw)
