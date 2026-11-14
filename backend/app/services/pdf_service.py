from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import settings
from app.errors import ProcessingError
from app.services.ocr_service import extract_image_text
from app.utils.files import derived_dir
from app.utils.logging import get_logger
from app.utils.text import clean_text

logger = get_logger(__name__)


@dataclass
class PdfPage:
    page_number: int
    text: str
    kind: str
    confidence: float
    provider: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class PdfResult:
    pages: list[PdfPage]
    metadata: dict[str, Any]
    page_count: int
    full_text: str


def extract_pdf(path: Path, evidence_id: uuid.UUID) -> PdfResult:
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise ProcessingError("PyMuPDF is not installed; PDF extraction is unavailable.") from exc

    try:
        document = fitz.open(path)
    except Exception as exc:
        raise ProcessingError("The PDF could not be opened.", {"error": str(exc)}) from exc

    if document.needs_pass:
        if not document.authenticate(""):
            document.close()
            raise ProcessingError("Password-protected PDFs cannot be processed automatically.")

    pages: list[PdfPage] = []
    ocr_errors: list[str] = []
    ocr_budget = settings.max_pdf_ocr_pages
    derived = derived_dir(evidence_id) / "pdf_pages"
    derived.mkdir(parents=True, exist_ok=True)

    try:
        metadata = dict(document.metadata or {})
        for index in range(document.page_count):
            page = document.load_page(index)
            text = clean_text(page.get_text("text"))
            if len(text) >= 25:
                pages.append(
                    PdfPage(
                        page_number=index + 1,
                        text=text,
                        kind="pdf_text",
                        confidence=0.99,
                        provider="pymupdf",
                    )
                )
                continue
            if ocr_budget <= 0:
                pages.append(
                    PdfPage(
                        page_number=index + 1,
                        text=text,
                        kind="pdf_text",
                        confidence=0.3,
                        provider="pymupdf",
                        meta={"note": "No embedded text; OCR page budget exhausted."},
                    )
                )
                continue
            ocr_budget -= 1
            image_path = derived / f"page_{index + 1:04d}.png"
            try:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pixmap.save(image_path)
                ocr = extract_image_text(image_path)
                pages.append(
                    PdfPage(
                        page_number=index + 1,
                        text=ocr.text,
                        kind="pdf_ocr",
                        confidence=ocr.confidence,
                        provider=ocr.provider,
                        meta={"framePath": str(image_path)},
                    )
                )
            except Exception as exc:  # noqa: BLE001 - keep readable pages
                ocr_errors.append(f"page {index + 1}: {exc}")
                pages.append(
                    PdfPage(
                        page_number=index + 1,
                        text=text,
                        kind="pdf_text",
                        confidence=0.2,
                        provider="pymupdf",
                        meta={"note": f"OCR unavailable: {exc}"},
                    )
                )
        page_count = document.page_count
    finally:
        document.close()

    readable = [page for page in pages if page.text.strip()]
    if not readable:
        raise ProcessingError(
            "No text could be extracted from this PDF. It may be image-only and OCR is unavailable.",
            {"ocrErrors": ocr_errors[:5]},
        )

    full_text = "\n\n".join(f"[Page {page.page_number}]\n{page.text}" for page in pages if page.text.strip())
    metadata.update(
        {
            "pages": page_count,
            "ocrErrors": ocr_errors[:10],
            "ocrEngine": next((page.provider for page in pages if page.kind == "pdf_ocr"), None),
            "hasScannedPages": any(page.kind == "pdf_ocr" for page in pages),
        }
    )
    return PdfResult(pages=pages, metadata=metadata, page_count=page_count, full_text=full_text)
