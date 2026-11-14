from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Configure an isolated test environment BEFORE importing the application.
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="tracevault-test-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{(_TEST_ROOT / 'test.db').as_posix()}",
    UPLOAD_DIR=str(_TEST_ROOT / "uploads"),
    AUTO_CREATE_TABLES="true",
    GEMINI_API_KEY="",
    OCR_ENGINE="none",
    WHISPER_MODEL="tiny",
    LOG_LEVEL="WARNING",
    READ_ONLY_ORIGINALS="false",
    ENVIRONMENT="test",
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def sample_pdf() -> Path:
    import fitz

    path = _TEST_ROOT / "incident_note.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(
        fitz.Rect(60, 60, 540, 760),
        "INCIDENT NOTE\n\n"
        "On 10 November 2026 at 22:14, Arjun Mehta sent a threat message to Priya Sharma. "
        "He used the phone +91 98200 41127 and the email arjun.mehta@example.com.\n\n"
        "On 11 November 2026 at 08:05, INR 18,50,000 was transferred to Rao Enterprises. "
        "Priya Sharma confirmed the payment in a WhatsApp message.\n\n"
        "A follow-up note was dated 12 November 2026.",
        fontsize=11,
    )
    document.save(path)
    document.close()
    return path
