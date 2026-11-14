from __future__ import annotations

from enum import Enum


class FileType(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    CHAT = "chat"
    DATA = "data"


class EvidenceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IntegrityStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    MISMATCH = "mismatch"


class ProcessingStage(str, Enum):
    QUEUED = "queued"
    STARTING = "starting"
    TEXT_EXTRACTION = "text_extraction"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    RAG_INDEXING = "rag_indexing"
    ENTITY_EXTRACTION = "entity_extraction"
    TIMELINE_RECONSTRUCTION = "timeline_reconstruction"
    INTEGRITY_CHECK = "integrity_check"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentKind(str, Enum):
    OCR = "ocr"
    PDF_TEXT = "pdf_text"
    PDF_OCR = "pdf_ocr"
    TRANSCRIPT = "transcript"
    FRAME_OCR = "frame_ocr"
    TEXT = "text"
    METADATA = "metadata"


class EntityType(str, Enum):
    PERSON = "person"
    PHONE = "phone"
    EMAIL = "email"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    EVENT = "event"
    OTHER = "other"


class EventCategory(str, Enum):
    COMMUNICATION = "Communication"
    FINANCIAL = "Financial"
    PHYSICAL = "Physical"
    DIGITAL = "Digital"
    LEGAL = "Legal"
    OTHER = "Other"


class AuditResult(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    DENIED = "denied"


class ReportStatus(str, Enum):
    DRAFT = "Draft"
    FINAL = "Final"
    REVIEW = "Review"
