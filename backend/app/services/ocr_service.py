from __future__ import annotations

import importlib.util
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import settings
from app.errors import ProcessingError
from app.services.ai_service import ai_service
from app.utils.logging import get_logger
from app.utils.text import clean_text

logger = get_logger(__name__)

_readers: dict[str, Any] = {}
_ocr_lock = threading.Lock()


@dataclass
class OCRBlock:
    text: str
    confidence: float
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0


@dataclass
class OCRResult:
    text: str
    confidence: float
    provider: str
    language: str | None = None
    blocks: list[OCRBlock] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def _easyocr_reader():
    if "easyocr" not in _readers:
        import easyocr  # type: ignore

        languages = [lang.strip() for lang in settings.ocr_languages.split(",") if lang.strip()] or ["en"]
        logger.info("Loading EasyOCR reader (languages=%s, gpu=%s)", languages, settings.ocr_gpu)
        _readers["easyocr"] = easyocr.Reader(languages, gpu=settings.ocr_gpu, verbose=False)
    return _readers["easyocr"]


def _run_easyocr(path: Path) -> OCRResult:
    reader = _easyocr_reader()
    raw = reader.readtext(str(path), detail=1, paragraph=False)
    blocks: list[OCRBlock] = []
    for item in raw:
        bbox, text, confidence = item[0], str(item[1]), float(item[2])
        xs = [float(point[0]) for point in bbox]
        ys = [float(point[1]) for point in bbox]
        blocks.append(
            OCRBlock(
                text=text,
                confidence=confidence,
                x=min(xs),
                y=min(ys),
                width=max(xs) - min(xs),
                height=max(ys) - min(ys),
            )
        )
    return _assemble(blocks, provider="easyocr")


def _run_paddleocr(path: Path) -> OCRResult:
    from paddleocr import PaddleOCR  # type: ignore

    languages = (settings.ocr_languages.split(",") or ["en"])[0].strip() or "en"
    if "paddle" not in _readers:
        logger.info("Loading PaddleOCR reader")
        try:
            _readers["paddle"] = PaddleOCR(use_angle_cls=True, lang=languages, show_log=False)
        except TypeError:
            _readers["paddle"] = PaddleOCR(lang=languages)
    ocr = _readers["paddle"]
    blocks: list[OCRBlock] = []
    try:
        result = ocr.ocr(str(path), cls=True)
    except (AttributeError, TypeError):
        result = ocr.predict(str(path))
    for page in result or []:
        for line in page or []:
            try:
                bbox, (text, confidence) = line[0], line[1]
                xs = [point[0] for point in bbox]
                ys = [point[1] for point in bbox]
                blocks.append(
                    OCRBlock(
                        text=str(text),
                        confidence=float(confidence),
                        x=min(xs),
                        y=min(ys),
                        width=max(xs) - min(xs),
                        height=max(ys) - min(ys),
                    )
                )
            except (TypeError, ValueError, IndexError):
                continue
    return _assemble(blocks, provider="paddleocr")


def _run_tesseract(path: Path) -> OCRResult:
    import pytesseract  # type: ignore
    from PIL import Image

    data = pytesseract.image_to_data(Image.open(path), output_type=pytesseract.Output.DICT)
    blocks: list[OCRBlock] = []
    for index, text in enumerate(data.get("text", [])):
        if not str(text).strip():
            continue
        try:
            confidence = float(data["conf"][index]) / 100
        except (TypeError, ValueError):
            confidence = 0.5
        blocks.append(
            OCRBlock(
                text=str(text).strip(),
                confidence=confidence,
                x=float(data["left"][index]),
                y=float(data["top"][index]),
                width=float(data["width"][index]),
                height=float(data["height"][index]),
            )
        )
    return _assemble(blocks, provider="tesseract")


def _run_gemini(path: Path) -> OCRResult:
    import mimetypes

    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    text = ai_service.extract_text_from_image(path.read_bytes(), mime)
    return OCRResult(text=clean_text(text), confidence=0.85, provider="gemini_vision")


def _assemble(blocks: list[OCRBlock], provider: str) -> OCRResult:
    if not blocks:
        return OCRResult(text="", confidence=0.0, provider=provider, blocks=[])
    ordered = sorted(blocks, key=lambda block: (round(block.y / max(block.height, 1)), block.x))
    lines: list[list[OCRBlock]] = []
    for block in ordered:
        if not lines:
            lines.append([block])
            continue
        last = lines[-1]
        baseline = max(item.y + item.height / 2 for item in last)
        if abs(block.y + block.height / 2 - baseline) <= max(block.height * 0.75, 10):
            last.append(block)
        else:
            lines.append([block])
    text = clean_text("\n".join("  ".join(item.text for item in sorted(line, key=lambda b: b.x)) for line in lines))
    confidence = float(sum(float(block.confidence) for block in blocks) / len(blocks))
    return OCRResult(text=text, confidence=round(confidence, 4), provider=provider, blocks=blocks)


def _engine_order() -> list[str]:
    configured = settings.ocr_engine.lower().strip()
    if configured in {"easyocr", "paddleocr", "tesseract", "gemini"}:
        return [configured]
    available: list[str] = []
    if importlib.util.find_spec("easyocr"):
        available.append("easyocr")
    if importlib.util.find_spec("paddleocr"):
        available.append("paddleocr")
    if importlib.util.find_spec("pytesseract"):
        available.append("tesseract")
    if settings.gemini_vision_fallback and ai_service.configured:
        available.append("gemini")
    return available


def available_ocr_engines() -> dict[str, bool]:
    return {
        "easyocr": importlib.util.find_spec("easyocr") is not None,
        "paddleocr": importlib.util.find_spec("paddleocr") is not None,
        "tesseract": importlib.util.find_spec("pytesseract") is not None,
        "gemini": ai_service.configured and settings.gemini_vision_fallback,
    }


def extract_image_text(path: Path, languages: str | None = None) -> OCRResult:
    if not path.exists():
        raise ProcessingError("Image file is missing for OCR.")
    errors: list[str] = []
    with _ocr_lock:
        for engine in _engine_order():
            try:
                if engine == "easyocr":
                    return _run_easyocr(path)
                if engine == "paddleocr":
                    return _run_paddleocr(path)
                if engine == "tesseract":
                    return _run_tesseract(path)
                if engine == "gemini":
                    return _run_gemini(path)
            except Exception as exc:  # noqa: BLE001 - engine failures are aggregated
                logger.warning("OCR engine %s failed for %s: %s", engine, path.name, exc)
                errors.append(f"{engine}: {exc}")
                continue
    detail = "; ".join(errors) or (
        "No OCR engine is available. Install EasyOCR (requirements.txt) or set GEMINI_API_KEY "
        "with GEMINI_VISION_FALLBACK=true."
    )
    raise ProcessingError("Text extraction failed because OCR is unavailable.", {"engines": detail})
