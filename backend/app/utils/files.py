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
    "opus": (FileType.AUDIO, "audio/opus"),
    "aiff": (FileType.AUDIO, "audio/aiff"),
    "aif": (FileType.AUDIO, "audio/aiff"),
    "wma": (FileType.AUDIO, "audio/x-ms-wma"),
    "amr": (FileType.AUDIO, "audio/amr"),
    "mp4": (FileType.VIDEO, "video/mp4"),
    "m4v": (FileType.VIDEO, "video/x-m4v"),
    "mov": (FileType.VIDEO, "video/quicktime"),
    "mkv": (FileType.VIDEO, "video/x-matroska"),
    "webm": (FileType.VIDEO, "video/webm"),
    "avi": (FileType.VIDEO, "video/x-msvideo"),
    "wmv": (FileType.VIDEO, "video/x-ms-wmv"),
    "flv": (FileType.VIDEO, "video/x-flv"),
    "mpg": (FileType.VIDEO, "video/mpeg"),
    "mpeg": (FileType.VIDEO, "video/mpeg"),
    "3gp": (FileType.VIDEO, "video/3gpp"),
    "ogv": (FileType.VIDEO, "video/ogg"),
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


# Extensions that are commonly mislabelled by download tools (e.g. "*.mp3.mpeg").
# For these we trust the file's actual signature over the extension.
AMBIGUOUS_MEDIA_EXTS = {
    "mpeg", "mpg", "mp4", "m4v", "m4a", "aac", "ogg", "ogv", "opus",
    "webm", "mkv", "wmv", "wma", "3gp", "flv", "avi", "amr", "aiff", "aif",
}


def sniff_media(path: Path) -> tuple[FileType, str] | None:
    """Detect an audio/video type from magic bytes when the extension is unreliable."""
    try:
        with path.open("rb") as handle:
            head = handle.read(65536)
    except OSError:
        return None
    if not head:
        return None
    if head.startswith(b"ID3") or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return FileType.AUDIO, "audio/mpeg"
    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return FileType.AUDIO, "audio/wav"
    if head.startswith(b"RIFF") and head[8:12] == b"AVI ":
        return FileType.VIDEO, "video/x-msvideo"
    if head.startswith(b"fLaC"):
        return FileType.AUDIO, "audio/flac"
    if head.startswith(b"OggS"):
        return FileType.AUDIO, "audio/ogg"
    if head.startswith(b"FORM") and head[8:12] in {b"AIFF", b"AIFC"}:
        return FileType.AUDIO, "audio/aiff"
    if head.startswith(b"#!AMR"):
        return FileType.AUDIO, "audio/amr"
    if head.startswith(b"FLV"):
        return FileType.VIDEO, "video/x-flv"
    if head.startswith(b"\x00\x00\x01\xba") or head.startswith(b"\x00\x00\x01\xb3"):
        return FileType.VIDEO, "video/mpeg"
    return None


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
    if ext in {"mp4", "mov", "m4a", "m4v", "3gp"}:
        return len(head) >= 12 and head[4:8] == b"ftyp"
    if ext == "wav":
        return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
    if ext == "avi":
        return head.startswith(b"RIFF") and head[8:12] == b"AVI "
    if ext == "mp3":
        return head.startswith(b"ID3") or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)
    if ext == "aac":
        # ADTS frames start with 0xFFF; some tools wrap AAC in an MP4 container.
        return (head[0] == 0xFF and (head[1] & 0xF6) == 0xF0) or (
            len(head) >= 12 and head[4:8] == b"ftyp"
        )
    if ext in {"ogg", "opus", "ogv"}:
        return head.startswith(b"OggS")
    if ext == "flac":
        return head.startswith(b"fLaC")
    if ext in {"mkv", "webm"}:
        return head.startswith(b"\x1aE\xdf\xa3")
    if ext in {"wmv", "wma"}:
        return head.startswith(b"\x30\x26\xb2\x75\x8e\x66\xcf\x11")
    if ext == "flv":
        return head.startswith(b"FLV")
    if ext in {"mpg", "mpeg"}:
        # MPEG can be a program stream, transport stream, or MPEG audio (MP3).
        return (
            head.startswith(b"\x00\x00\x01\xba")
            or head.startswith(b"\x00\x00\x01\xb3")
            or head.startswith(b"ID3")
            or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)
        )
    if ext in {"aiff", "aif"}:
        return head.startswith(b"FORM") and head[8:12] in {b"AIFF", b"AIFC"}
    if ext == "amr":
        return head.startswith(b"#!AMR")
    if ext in {"txt", "json", "csv", "eml"}:
        return True
    # Unknown containers for an allowed extension: trust the extension rather
    # than rejecting a valid media file we don't have a signature rule for.
    return True


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
