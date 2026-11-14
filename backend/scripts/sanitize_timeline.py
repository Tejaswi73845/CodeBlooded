"""Rewrite stored timeline titles that were copied verbatim from email headers.

Run from ``backend/``:

    .venv\\Scripts\\python scripts/sanitize_timeline.py [--dry-run]

The script is idempotent:
* header-shaped titles become ``Email from X to Y: subject``;
* ``Name <address>`` angle brackets and bare IPs are removed from titles;
* duplicate events that exist only because a header block was read as an event are dropped;
* cached AI summaries that quote header syntax or repeat the card's own date are cleared
  so they regenerate with the current prompt.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import EventEntity, Evidence, TimelineEvent
from app.models.enums import EventCategory
from app.utils.email_headers import is_header_block, sanitize_event_title
from app.utils.narrative import sanitize_summary
from app.utils.text import clean_text


def _is_header_event(title: str) -> bool:
    normalized = clean_text(title)
    if not normalized:
        return False
    if is_header_block(normalized):
        return True
    return normalized.lower().startswith(("from:", "to:", "date:", "subject:", "message-id:"))


def _needs_summary_refresh(summary: str, occurred_at_raw: str | None) -> bool:
    return bool(summary) and sanitize_summary(summary, occurred_at_raw) != clean_text(summary)


def run(dry_run: bool = False) -> dict[str, int]:
    stats = {"renamed": 0, "removed": 0, "cleared": 0, "evidence_cleared": 0}
    db = SessionLocal()
    try:
        for evidence in db.scalars(select(Evidence)).all():
            events = list(
                db.scalars(select(TimelineEvent).where(TimelineEvent.evidence_id == evidence.id)).all()
            )
            header_event_ids: set = set()

            for event in events:
                original = event.title or ""
                sanitized = sanitize_event_title(original, 250)
                header_event = _is_header_event(original)
                if header_event:
                    header_event_ids.add(event.id)
                if sanitized and sanitized != original:
                    event.title = sanitized
                    stats["renamed"] += 1

                meta = dict(event.meta or {})
                cached = meta.get("aiSummary")
                if isinstance(cached, dict):
                    summary = str(cached.get("summary") or "")
                    if header_event or _needs_summary_refresh(summary, event.occurred_at_raw):
                        meta.pop("aiSummary", None)
                        stats["cleared"] += 1
                if meta != (event.meta or {}):
                    event.meta = meta
                db.add(event)

            # Drop header-derived duplicates when a cleaner communication event has the
            # same minute (the header and the AI extraction describe the same message).
            removed_ids: set = set()
            for event in events:
                if event.id not in header_event_ids or event.occurred_at is None:
                    continue
                minute = event.occurred_at.replace(second=0, microsecond=0)
                duplicate = any(
                    other.id != event.id
                    and other.id not in header_event_ids
                    and other.id not in removed_ids
                    and other.occurred_at is not None
                    and other.occurred_at.replace(second=0, microsecond=0) == minute
                    and other.category == EventCategory.COMMUNICATION
                    for other in events
                )
                if duplicate:
                    removed_ids.add(event.id)
                    db.execute(delete(EventEntity).where(EventEntity.event_id == event.id))
                    db.delete(event)
                    stats["removed"] += 1

            meta = dict(evidence.meta or {})
            cached = meta.get("aiSummary")
            if isinstance(cached, dict):
                summary = str(cached.get("summary") or "")
                if _needs_summary_refresh(summary, None):
                    meta.pop("aiSummary", None)
                    evidence.meta = meta
                    db.add(evidence)
                    stats["evidence_cleared"] += 1

        if dry_run:
            db.rollback()
        else:
            db.commit()
    finally:
        db.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitise stored timeline titles and summaries.")
    parser.add_argument("--dry-run", action="store_true", help="report changes without saving them")
    args = parser.parse_args()
    stats = run(dry_run=args.dry_run)
    suffix = " (dry run, nothing saved)" if args.dry_run else ""
    print(
        f"titles rewritten: {stats['renamed']} | header duplicates removed: {stats['removed']} | "
        f"event summaries cleared: {stats['cleared']} | evidence summaries cleared: "
        f"{stats['evidence_cleared']}{suffix}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
