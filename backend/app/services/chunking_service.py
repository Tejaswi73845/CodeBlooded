from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.models import ExtractedContent
from app.models.enums import ContentKind
from app.utils.text import clean_text, split_sentences

MIN_CHUNK_CHARS = 20


@dataclass
class ChunkDraft:
    content_id: uuid.UUID
    chunk_index: int
    text: str
    content_kind: str
    page_number: int | None
    timestamp_start: float | None
    timestamp_end: float | None
    content_hash: str
    meta: dict[str, Any] = field(default_factory=dict)


def _tail_overlap(text: str, overlap: int) -> str:
    if overlap <= 0 or not text:
        return ""
    tail = text[-overlap:]
    if " " in tail:
        tail = tail.split(" ", 1)[1]
    return tail.strip()


def split_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    size = size or settings.rag_chunk_size
    overlap = min(overlap if overlap is not None else settings.rag_chunk_overlap, max(0, size // 2))
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    current = ""
    for sentence in split_sentences(text):
        if len(sentence) > size:
            if current:
                chunks.append(current)
                current = ""
            step = max(1, size - overlap)
            for start in range(0, len(sentence), step):
                piece = sentence[start : start + size].strip()
                if piece:
                    chunks.append(piece)
                if start + size >= len(sentence):
                    break
            continue

        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > size:
            chunks.append(current)
            current = f"{_tail_overlap(current, overlap)} {sentence}".strip()
        else:
            current = candidate

    if current:
        chunks.append(current)

    # Drop accidental near-duplicates created by overlap windows.
    result: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        normalized = " ".join(chunk.split())
        if not normalized or normalized in seen:
            continue
        if len(normalized) < MIN_CHUNK_CHARS and result:
            result[-1] = f"{result[-1]} {normalized}".strip()
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _transcript_chunks(content: ExtractedContent) -> list[ChunkDraft]:
    segments = (content.meta or {}).get("segments") or []
    drafts: list[ChunkDraft] = []
    if not isinstance(segments, list) or not segments:
        return drafts
    size = settings.rag_chunk_size
    buffer: list[dict[str, Any]] = []
    length = 0

    def flush() -> None:
        nonlocal buffer, length
        if not buffer:
            return
        text = clean_text(" ".join(str(segment.get("text", "")) for segment in buffer))
        if text:
            start = float(buffer[0].get("start", 0) or 0)
            end = float(buffer[-1].get("end", start) or start)
            drafts.append(
                _draft(
                    content,
                    len(drafts),
                    text,
                    timestamp_start=start,
                    timestamp_end=end,
                    meta={"segmentCount": len(buffer)},
                )
            )
        buffer = []
        length = 0

    for segment in segments:
        text = clean_text(str(segment.get("text", "")))
        if not text:
            continue
        if buffer and length + len(text) > size:
            flush()
        buffer.append(segment)
        length += len(text) + 1
    flush()
    return drafts


def _draft(
    content: ExtractedContent,
    index: int,
    text: str,
    *,
    page_number: int | None = None,
    timestamp_start: float | None = None,
    timestamp_end: float | None = None,
    meta: dict[str, Any] | None = None,
) -> ChunkDraft:
    page = page_number if page_number is not None else content.page_number
    start = timestamp_start if timestamp_start is not None else content.timestamp_start
    end = timestamp_end if timestamp_end is not None else content.timestamp_end
    digest = hashlib.sha256(
        f"{content.id}:{index}:{page or ''}:{start or ''}:{end or ''}:{text}".encode("utf-8")
    ).hexdigest()
    return ChunkDraft(
        content_id=content.id,
        chunk_index=index,
        text=text,
        content_kind=content.kind.value,
        page_number=page,
        timestamp_start=start,
        timestamp_end=end,
        content_hash=digest,
        meta=meta or {},
    )


def chunk_content(content: ExtractedContent) -> list[ChunkDraft]:
    text = clean_text(content.text)
    if not text:
        return []

    if content.kind == ContentKind.TRANSCRIPT:
        transcript = _transcript_chunks(content)
        if transcript:
            return transcript

    if content.kind == ContentKind.FRAME_OCR and len(text) <= settings.rag_chunk_size:
        return [
            _draft(
                content,
                0,
                text,
                timestamp_start=content.timestamp_start,
                timestamp_end=content.timestamp_end,
                meta={"frame": True},
            )
        ]

    return [_draft(content, index, chunk) for index, chunk in enumerate(split_text(text))]
