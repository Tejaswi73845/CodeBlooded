from __future__ import annotations

from types import SimpleNamespace

from app.services.timeline_service import _supplemental_events
from app.utils.email_headers import (
    header_event_title,
    is_header_block,
    sanitize_event_title,
)
from app.utils.narrative import (
    sanitize_summary,
    strip_header_syntax,
    trim_restated_time,
)

EMAIL_HEADERS = (
    "From: Karan Malhotra <karan.malhotra@brightpath-capital.in>\n"
    "To: Meera Iyer <meera.iyer@example.com>\n"
    "Date: Sun, 08 Feb 2026 09:10:44 +0530\n"
    "Subject: BrightPath Capital - Client Agreement and Onboarding Instructions\n"
    "Message-ID: <20260208091044.7F3A1@mail.brightpath-capital.in>\n"
    "X-Originating-IP: 203.0.113.45\n"
    "Attachments: BrightPath_Client_Agreement_MeeraIyer.pdf\n"
    "Dear Ma'am,\n"
    "Thank you for your interest in BrightPath Capital. Please find attached your\n"
    "Client Service and Investment Agreement."
)


def test_header_block_is_detected_multiline_and_collapsed():
    assert is_header_block(EMAIL_HEADERS)
    collapsed = " ".join(EMAIL_HEADERS.splitlines())
    assert is_header_block(collapsed)


def test_header_block_becomes_human_title():
    title = header_event_title(EMAIL_HEADERS)
    assert title.startswith("Email from Karan Malhotra to Meera Iyer")
    assert "BrightPath Capital - Client Agreement" in title
    assert "<" not in title and ">" not in title
    assert "Message-ID" not in title


def test_sanitize_rewrites_header_shaped_stored_title():
    stored = (
        "From: Karan Malhotra <karan.malhotra@brightpath-capital.in> To: Meera Iyer "
        "<meera.iyer@example.com> Date: Sun, 08 Feb 2026 09:10:44 +0530 Subject: BrightPath"
    )
    title = sanitize_event_title(stored)
    assert title.startswith("Email from Karan Malhotra to Meera Iyer")
    assert "<" not in title and ">" not in title


def test_sanitize_handles_title_truncated_by_old_110_char_limit():
    stored = (
        "From: Meera Iyer <meera.iyer@example.com> To: Cyber Crime Cell Bengaluru "
        "<cybercell.bengaluru@example.org> Da…"
    )
    assert sanitize_event_title(stored) == "Email from Meera Iyer to Cyber Crime Cell Bengaluru"


def test_sanitize_removes_angle_bracket_addresses_only():
    assert sanitize_event_title("Request to make first deposit") == "Request to make first deposit"
    assert (
        sanitize_event_title("Karan Malhotra <karan@example.com> sent the agreement")
        == "Karan Malhotra sent the agreement"
    )


def test_supplemental_email_event_uses_header_title():
    content = SimpleNamespace(
        text=EMAIL_HEADERS,
        page_number=None,
        timestamp_start=None,
    )
    events = _supplemental_events([content])
    header_events = [event for event in events if event.source == "regex_email_header"]
    assert header_events, "the email header block should yield one communication event"
    title = header_events[0].title
    assert title.startswith("Email from Karan Malhotra to Meera Iyer")
    assert "<" not in title
    description = header_events[0].description
    assert "Dear Ma'am" in description
    assert "From:" not in description and "Message-ID" not in description


def test_trim_restated_time_drops_leading_metadata():
    summary = (
        "On 08 Feb 2026 at 09:10, Karan Malhotra sent Meera Iyer the client agreement "
        "and asked her to sign and return the last page."
    )
    assert trim_restated_time(summary, "08 Feb 2026 09:10").startswith("Karan Malhotra sent")


def test_trim_restated_time_keeps_substantive_sentence():
    summary = (
        "Karan Malhotra demanded Rs. 25,000 from Meera Iyer before Tuesday, "
        "warning that the offer would lapse otherwise."
    )
    assert trim_restated_time(summary, "08 Feb 2026 09:10") == summary


def test_sanitize_summary_removes_header_syntax():
    summary = (
        "The email from Karan Malhotra had Message-ID <20260208091044.7F3A1@mail.brightpath-capital.in> "
        "and X-Originating-IP: 203.0.113.45."
    )
    cleaned = sanitize_summary(summary)
    assert "<" not in cleaned and ">" not in cleaned
    assert "Message-ID" not in cleaned
    assert "203.0.113.45" not in cleaned


def test_sanitize_summary_keeps_sentence_punctuation():
    assert strip_header_syntax("Karan Malhotra sent the agreement.") == "Karan Malhotra sent the agreement."
