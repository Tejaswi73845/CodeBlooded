from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient


def _upload(client: TestClient, path: Path, name: str | None = None):
    with path.open("rb") as handle:
        return client.post(
            "/api/evidence/upload",
            files=[("files", (name or path.name, handle, "application/pdf"))],
        )


def _wait(client: TestClient, evidence_id: str, timeout: float = 60.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        response = client.get(f"/api/evidence/{evidence_id}/status")
        assert response.status_code == 200, response.text
        last = response.json()
        if last["status"] in {"completed", "failed"}:
            return last
        time.sleep(0.25)
    raise AssertionError(f"Processing did not finish: {last}")


def test_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["ok"] is True


def test_end_to_end_workflow(client: TestClient, sample_pdf: Path):
    response = _upload(client, sample_pdf, "Incident_Note_10Nov.pdf")
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["accepted"] == 1
    evidence = payload["items"][0]
    evidence_id = evidence["id"]
    assert evidence["hash"]
    assert len(evidence["hash"]) == 64
    assert evidence["status"] in {"pending", "processing", "completed"}

    status = _wait(client, evidence_id)
    assert status["status"] == "completed", status
    assert status["integrity"] == "verified"
    assert status["progress"] == 100
    assert status["processingCompletedAt"].endswith("Z")

    detail = client.get(f"/api/evidence/{evidence_id}").json()
    assert detail["pages"] == 1
    assert detail["extractedContent"], "PDF text extraction produced no content"
    extracted = "\n".join(item["text"] for item in detail["extractedContent"])
    assert "Arjun Mehta" in extracted
    assert "18,50,000" in extracted
    assert detail["timelineEvents"], "No timeline events were reconstructed"

    events = client.get("/api/timeline", params={"personId": ""}).json()
    assert events["total"] >= 2
    november = [
        event for event in events["items"]
        if event["at"] and event["at"].startswith("2026-11-10")
    ]
    assert november, events["items"]
    assert any(event["timeUncertain"] for event in events["items"])

    entities = client.get("/api/entities").json()
    values = {item["normalizedValue"] for item in entities["items"]}
    assert any("arjun" in value for value in values), values
    assert any("@" in value for value in values), values

    graph = client.get("/api/entities/graph").json()
    assert graph["nodes"], "Graph is empty"
    assert "stats" in graph

    download = client.get(f"/api/evidence/{evidence_id}/download")
    assert download.status_code == 200
    assert download.headers["X-Evidence-SHA256"] == evidence["hash"]
    assert download.content.startswith(b"%PDF-")

    # Exact duplicate is warned about but preserved as a separate record.
    duplicate_response = _upload(client, sample_pdf, "Incident_Note_copy.pdf")
    assert duplicate_response.status_code == 202
    duplicate_payload = duplicate_response.json()
    assert duplicate_payload["duplicates"]
    assert duplicate_payload["duplicates"][0]["kind"] == "exact"
    assert duplicate_payload["items"][0]["id"] != evidence_id
    _wait(client, duplicate_payload["items"][0]["id"])

    # Evidence-grounded assistant works without Gemini via an extractive fallback.
    chat = client.post(
        "/api/assistant/chat",
        json={"question": "What happened on 10 November 2026?", "limit": 5},
    )
    assert chat.status_code == 200, chat.text
    answer = chat.json()
    assert answer["sources"], answer
    assert answer["insufficientEvidence"] is False
    assert answer["mode"] in {"extractive", "gemini"}

    irrelevant = client.post(
        "/api/assistant/chat",
        json={"question": "What is the launch code for the Mars mission?"},
    )
    assert irrelevant.status_code == 200
    assert irrelevant.json()["insufficientEvidence"] is True
    assert irrelevant.json()["sources"] == []

    verify = client.post(f"/api/evidence/{evidence_id}/verify")
    assert verify.status_code == 200
    assert verify.json()["integrity"] == "verified"

    report = client.post(
        "/api/reports/generate",
        json={"title": "End-to-end test report", "reportType": "incident"},
    )
    assert report.status_code == 201, report.text
    report_body = report.json()
    assert report_body["evidenceCount"] >= 2
    assert report_body["content"]["chronology"]
    assert report_body["content"]["integrity"]["verified"] >= 2

    pdf = client.get(f"/api/reports/{report_body['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")

    audit = client.get("/api/audit")
    assert audit.status_code == 200
    assert audit.json()["chainValid"] is True
    audit_verify = client.get("/api/audit/verify").json()
    assert audit_verify["valid"] is True

    # Soft delete preserves the original by design.
    deleted = client.delete(f"/api/evidence/{evidence_id}")
    assert deleted.status_code == 200
    listed = client.get("/api/evidence").json()
    assert all(item["id"] != evidence_id for item in listed["items"])

    not_found = client.get(f"/api/evidence/{evidence_id}")
    assert not_found.status_code == 404


def test_rejects_unsupported_extension(client: TestClient):
    response = client.post(
        "/api/evidence/upload",
        files=[("files", ("payload.exe", b"MZ\x90\x00", "application/octet-stream"))],
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "upload_failed"
