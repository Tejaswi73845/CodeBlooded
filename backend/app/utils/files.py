from __future__ import annotations

import hashlib
import mimetypes
import re
import uuid
from pathlib import Path

from app.config import settings
from app.models.enums import FileType

EXTENSION_MAP: dict[str, tuple[FileType, str]] = {
    "pdf": (FileType.DOCUMENT, "application/pdf"),
    "png": (FileType.IMAGE, "image/png"),
    "jpg": (FileType.IMAGE, "image/jpeg"),
    "jpeg": (FileType.IMAGE, "image/jpeg"),
    "mp3": (FileType.AUDIO, "audio/mpeg"),
    "wav": (FileType.AUDIO, "audio/wav"),
    "m4a": (FileType.AUDIO, "audio/mp4"),
    "aac": (FileType.AUDIO, "audio/aac"),
    "flac": (FileType.AUDIO, "audio/flac"),
    "ogg": (FileType.AUDIO, "audio/ogg"),
    "mp4": (FileType.VIDEO, "video/mp4"),
    "mov": (FileType.VIDEO, "video/quicktime"),
    "mkv": (FileType.VIDEO, "video/x-matroska"),
    "webm": (FileType.VIDEO, "video/webm"),
    "txt": (FileType.CHAT, "text/plain"),
    "eml": (FileType.CHAT, "message/rfc822"),
    "json": (FileType.DATA, "application/json"),
    "csv": (FileType.DATA, "text/csv"),
}


class UnsupportedFileError(ValueError):
    pass


def safe_filename(filename: str) -> str:
    name = Path(filename or "evidence").name
    name = re.sub(r"[^A-Za-z0-9._()\- ]+", "_", name).strip(" ._")
    if not name:
        name = "evidence"
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    return f"{stem[:180]}.{ext[:12].lower()}" if ext else stem[:180]


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def detect_file_type(filename: str, content_type: str | None = None) -> tuple[FileType, str]:
    ext = extension_of(filename)
    if ext not in settings.allowed_extension_set or ext not in EXTENSION_MAP:
        raise UnsupportedFileError(f"Unsupported file extension: .{ext or 'unknown'}")
    file_type, inferred_mime = EXTENSION_MAP[ext]
    mime = content_type if content_type and content_type != "application/octet-stream" else inferred_mime
    if mime == inferred_mime or inferred_mime.startswith(mime.split("/")[0]):
        mime = inferred_mime
    return file_type, mime


def verify_magic(path: Path, ext: str) -> bool:
    """Lightweight signature check to reject spoofed extensions."""
    try:
        with path.open("rb") as handle:
            head = handle.read(32)
    except OSError:
        return False
    if not head:
        return False
    if ext == "pdf":
        return head.startswith(b"%PDF-")
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {"jpg", "jpeg"}:
        return head.startswith(b"\xff\xd8\xff")
    if ext in {"mp4", "mov", "m4a"}:
        return len(head) >= 12 and head[4:8] == b"ftyp"
    if ext == "wav":
        return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
    if ext == "mp3":
        return head.startswith(b"ID3") or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)
    if ext == "ogg":
        return head.startswith(b"OggS")
    if ext == "flac":
        return head.startswith(b"fLaC")
    if ext in {"mkv", "webm"}:
        return head.startswith(b"\x1aE\xdf\xa3")
    if ext in {"txt", "json", "csv", "eml"}:
        return True
    return False


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_phash(path: Path) -> str | None:
    """64-bit difference hash (dHash); tolerant to resizing and compression."""
    try:
        from PIL import Image  # imported lazily to keep API startup light

        with Image.open(path) as image:
            pixels = list(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).getdata())
        bits = 0
        for row in range(8):
            for column in range(8):
                left = pixels[row * 9 + column]
                right = pixels[row * 9 + column + 1]
                bits = (bits << 1) | (1 if left > right else 0)
        return f"{bits:016x}"
    except Exception:  # pragma: no cover - corrupt image / unavailable Pillow
        return None


def hamming_distance(first: str, second: str) -> int:
    try:
        return bin(int(first, 16) ^ int(second, 16)).count("1")
    except (ValueError, TypeError):
        return 64


def original_dir(evidence_id: uuid.UUID) -> Path:
    return settings.upload_root / "originals" / str(evidence_id)


def derived_dir(evidence_id: uuid.UUID) -> Path:
    return settings.upload_root / "derived" / str(evidence_id)


def ensure_within(base: Path, candidate: Path) -> Path:
    base = base.resolve()
    candidate = candidate.resolve()
    if base != candidate and base not in candidate.parents:
        raise ValueError("Resolved path escapes the upload root")
    return candidate


def validate_stored_path(stored: str) -> Path:
    candidate = Path(stored)
    if not candidate.is_absolute():
        candidate = settings.upload_root / candidate
    return ensure_within(settings.upload_root, candidate)


def guess_mime(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"
