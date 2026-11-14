from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import Request

from app.config import settings
from app.errors import AppError
from app.utils.time import utcnow


def optional_uuid(value: str | None, field: str = "id") -> uuid.UUID | None:
    """Accept empty query values (common in JS clients) without a 422 storm."""
    if value is None:
        return None
    cleaned = str(value).strip()
    if cleaned == "" or cleaned.lower() == "null":
        return None
    try:
        return uuid.UUID(cleaned)
    except (ValueError, AttributeError, TypeError) as exc:
        raise AppError(422, "invalid_id", f"`{field}` must be a valid UUID.") from exc


def actor_name(request: Request | None) -> str:
    if request is None:
        return settings.default_actor
    header = request.headers.get("x-actor") or request.headers.get("x-user-name")
    if header:
        return header.strip()[:160]
    return settings.default_actor


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def user_agent(request: Request | None) -> str | None:
    if request is None:
        return None
    return (request.headers.get("user-agent") or "")[:512] or None


def parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        try:
            from dateutil import parser as dateutil_parser

            return dateutil_parser.parse(cleaned).replace(tzinfo=None)
        except (ValueError, OverflowError):
            return None


def now_iso() -> str:
    return utcnow().isoformat()
