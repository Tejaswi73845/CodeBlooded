from __future__ import annotations

import re
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from dateutil import parser as dateutil_parser

from app.config import settings

MONTH_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"),
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH_PATTERN}(?:\s+\d{{4}})?\b", re.I),
    re.compile(rf"\b{MONTH_PATTERN}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s*\d{{4}})?\b", re.I),
    re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?\d{1,2}:\d{2}\s*(?:am|pm)?\b", re.I),
]
TIME_PATTERN = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*[ap]m)?\b", re.I)
DATE_TIME_COMBINED = re.compile(
    rf"(?:{DATE_PATTERNS[0].pattern}|{DATE_PATTERNS[1].pattern}|{DATE_PATTERNS[2].pattern}|{DATE_PATTERNS[3].pattern})"
    rf"(?:\s*(?:at|,)?\s*{TIME_PATTERN.pattern})?",
    re.I,
)


def utcnow() -> datetime:
    """Naive UTC timestamp used consistently across SQLite and PostgreSQL."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_naive(value: datetime, assume_tz: str | None = None) -> datetime:
    if value.tzinfo is None:
        zone = ZoneInfo(assume_tz or settings.timezone)
        value = value.replace(tzinfo=zone)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def parse_event_datetime(raw: str, assume_tz: str | None = None) -> tuple[datetime | None, bool]:
    """Parse a date/time expression. Returns (naive UTC datetime, time_uncertain)."""
    text = raw.strip()
    if not text:
        return None, True
    has_time = bool(TIME_PATTERN.search(text)) or bool(re.search(r"\b(noon|midnight)\b", text, re.I))
    try:
        default = datetime.combine(datetime.now().date(), time(0, 0))
        parsed = dateutil_parser.parse(text, default=default, fuzzy=True)
    except (ValueError, OverflowError, TypeError):
        return None, True
    if parsed.year < 1900 or parsed.year > 2100:
        return None, True
    return to_utc_naive(parsed, assume_tz), not has_time


def find_date_expressions(text: str) -> list[str]:
    seen: set[str] = set()
    found: list[str] = []
    for match in DATE_TIME_COMBINED.finditer(text):
        raw = match.group(0).strip(" ,.;")
        if raw and raw.lower() not in seen:
            seen.add(raw.lower())
            found.append(raw)
    return found


def format_duration(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
