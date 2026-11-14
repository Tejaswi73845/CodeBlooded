"""Detection and cleanup of RFC822-style email headers in extracted evidence text.

Email exports begin with header lines such as ``From:``, ``To:`` and ``Message-ID:``.
Those lines are metadata, but the sentence splitter treats the whole block as one
"sentence" and it often carries a date, so it used to be emitted verbatim as a
timeline event title. These helpers derive a human label instead and strip the
``Name <address>`` angle-bracket syntax that leaked into titles.
"""

from __future__ import annotations

import re

from app.utils.text import clean_text, truncate

HEADER_LABEL = re.compile(
    r"(?i)\b(from|to|cc|bcc|date|sent|subject|reply-to|message-id|mime-version|"
    r"content-type|attachments|x-[a-z0-9-]+)\s*:"
)
CORE_HEADERS = {"from", "to", "cc", "bcc", "subject", "date", "sent"}
ANGLE_ADDRESS = re.compile(r"<\s*[^<>@\s]+@[^<>\s]+\s*>")
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
ADDRESS_SPLIT = re.compile(r",(?![^<]*>)")
SUBJECT_PREFIX = re.compile(r"(?i)^\s*(?:re|fw|fwd|aw)\s*:\s*")
WHITESPACE = re.compile(r"\s+")

MAX_TITLE = 140


def header_keys(text: str | None) -> list[str]:
    """Header labels present in ``text``, in order of appearance."""
    return [match.group(1).lower() for match in HEADER_LABEL.finditer(clean_text(text))]


def is_header_block(text: str | None) -> bool:
    """True when the text is (mostly) an email header block, on one line or many."""
    keys = header_keys(text)
    if len(keys) < 2:
        return False
    return bool(CORE_HEADERS.intersection(keys))


def parse_headers(text: str | None) -> dict[str, str]:
    """Map header labels to their values, tolerating folded and collapsed lines."""
    raw = clean_text(text)
    matches = list(HEADER_LABEL.finditer(raw))
    headers: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        key = match.group(1).lower()
        value = _folded_value(raw[match.end() : end])
        if value and key not in headers:
            headers[key] = value
    return headers


def _folded_value(segment: str) -> str:
    """Keep the first line plus indented continuation lines only."""
    lines = segment.strip(" \t\n,;").splitlines()
    if not lines:
        return ""
    kept = [lines[0].strip()]
    for line in lines[1:]:
        if not line[:1] or not line[:1].isspace():
            break
        kept.append(line.strip())
    value = WHITESPACE.sub(" ", " ".join(kept)).strip(" \t\n,;")
    # Drop the tail of a header label that was cut off by title truncation ("Da…").
    return re.sub(r"\s+[A-Za-z]{1,4}…$", "", value).strip()


def display_name(value: str | None) -> str:
    """``Karan Malhotra <karan@example.com>`` -> ``Karan Malhotra``."""
    value = (value or "").strip()
    if not value:
        return ""
    angled = ANGLE_ADDRESS.search(value)
    name = ANGLE_ADDRESS.sub("", value)
    if "<" in name:
        name = name.split("<", 1)[0]
    name = name.strip().strip("\"'").strip()
    if name:
        return name
    if angled:
        return angled.group(0).strip("<> ").strip()
    return value


def recipient_names(value: str | None) -> list[str]:
    parts = [part for part in ADDRESS_SPLIT.split(value or "") if part.strip()]
    names = [display_name(part) for part in parts]
    return [name for name in names if name]


def _join_names(names: list[str]) -> str:
    if len(names) <= 2:
        return " and ".join(names)
    return f"{names[0]} and {len(names) - 1} others"


def _subject(value: str | None) -> str:
    subject = SUBJECT_PREFIX.sub("", value or "").strip(" \t,;")
    subject = WHITESPACE.sub(" ", subject)
    if subject.endswith("…"):
        subject = subject[:-1].rstrip()
        subject = subject.rsplit(" ", 1)[0] if " " in subject else ""
    if len(subject) < 3:
        return ""
    return truncate(subject, 90)


def header_event_title(text: str | None) -> str:
    """A readable label for an email described by its header block."""
    headers = parse_headers(text)
    sender = display_name(headers.get("from", ""))
    recipients = recipient_names(headers.get("to") or headers.get("cc") or "")
    subject = _subject(headers.get("subject", ""))

    if sender and recipients:
        label = f"Email from {sender} to {_join_names(recipients)}"
    elif sender:
        label = f"Email from {sender}"
    elif recipients:
        label = f"Email to {_join_names(recipients)}"
    else:
        label = "Email"
    if subject:
        label = f"{label}: {subject}"
    return truncate(label, MAX_TITLE)


def strip_header_block(text: str | None) -> str:
    """Return the body that follows a leading block of header lines."""
    lines = clean_text(text).splitlines()
    index = 0
    seen = False
    while index < len(lines):
        line = lines[index]
        if HEADER_LABEL.match(line):
            seen = True
            index += 1
            continue
        if seen and line.startswith((" ", "\t")):
            index += 1
            continue
        break
    if not seen:
        return clean_text(text)
    return "\n".join(lines[index:]).strip()


def header_event_description(text: str | None) -> str:
    """Body text for a header-derived event, falling back to the subject."""
    body = strip_header_block(text)
    if body:
        return body
    return _subject(parse_headers(text).get("subject", ""))


def header_digest(text: str | None) -> str:
    """Compact ``From/To/Date/Subject`` summary used instead of raw headers in prompts."""
    headers = parse_headers(text)
    lines: list[str] = []
    sender = display_name(headers.get("from", ""))
    recipients = recipient_names(headers.get("to") or headers.get("cc") or "")
    if sender:
        lines.append(f"From: {sender}")
    if recipients:
        lines.append(f"To: {_join_names(recipients)}")
    date = headers.get("date") or headers.get("sent")
    if date:
        lines.append(f"Date: {date}")
    subject = _subject(headers.get("subject", ""))
    if subject:
        lines.append(f"Subject: {subject}")
    return "\n".join(lines)


def sanitize_event_title(title: str | None, limit: int = MAX_TITLE) -> str:
    """Turn a stored title into a clean human label.

    Header blocks are replaced by ``Email from X to Y: subject``; angle-bracket
    addresses and bare IPs are removed. Ordinary titles are left byte-for-byte
    unchanged. Returns ``""`` when nothing usable is left.
    """
    raw = (title or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return ""

    keys = header_keys(raw)
    starts_with_header = bool(HEADER_LABEL.match(raw))
    if is_header_block(raw) or starts_with_header or ("from" in keys and len(keys) > 1):
        generated = header_event_title(raw)
        if generated and generated != "Email":
            return truncate(generated, limit)
        if starts_with_header:
            return ""

    text = ANGLE_ADDRESS.sub("", raw)
    text = IPV4.sub("", text)
    if text == raw:
        return truncate(raw, limit)
    text = WHITESPACE.sub(" ", text).strip(" ,.;:-")
    return truncate(text, limit) if len(text) >= 2 else ""
