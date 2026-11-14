from __future__ import annotations

import uuid

import pytest

from app.database import SessionLocal
from app.errors import AIInvalidResponse, AIServiceUnavailable
from app.models import DocumentChunk, Evidence, ExtractedContent
from app.models.enums import ContentKind, EvidenceStatus, FileType, IntegrityStatus, ProcessingStage
from app.services import assistant_service, retrieval_service
from app.services.ai_service import ai_service
from app.services.chunking_service import chunk_content, split_text
from app.services.retrieval_service import cosine_similarity, lexical_score
from app.utils.time import utcnow


def test_chunking_preserves_pages_and_timestamps():
    transcript = ExtractedContent(
        id=uuid.uuid4(),
        evidence_id=uuid.uuid4(),
        kind=ContentKind.TRANSCRIPT,
        text="The transfer was completed on 11 November. Rohan Kapoor witnessed the conversation.",
        meta={
            "segments": [
                {"start": 0.0, "end": 4.2, "text": "The transfer was completed on 11 November."},
                {"start": 4.4, "end": 9.8, "text": "Rohan Kapoor witnessed the conversation."},
            ]
        },
    )
    chunks = chunk_content(transcript)
    assert chunks
    assert chunks[0].timestamp_start == 0.0
    assert chunks[0].timestamp_end >= 4.2

    pdf_page = ExtractedContent(
        id=uuid.uuid4(),
        evidence_id=uuid.uuid4(),
        kind=ContentKind.PDF_TEXT,
        text="On 10 November 2026 Arjun Mehta demanded a transfer. " * 30,
        page_number=4,
    )
    page_chunks = chunk_content(pdf_page)
    assert len(page_chunks) > 1
    assert all(chunk.page_number == 4 for chunk in page_chunks)
    assert all(len(chunk.text) <= 1400 for chunk in page_chunks)


def test_split_text_overlap_and_cosine():
    text = "Sentence one about evidence. " * 80
    chunks = split_text(text, size=300, overlap=50)
    assert len(chunks) > 2
    assert all(chunks)
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert lexical_score("the transfer was completed", ["transfer", "completed"]) > 0


@pytest.fixture
def rag_evidence(client):
    db = SessionLocal()
    evidence = Evidence(
        reference=f"TV-TEST-{uuid.uuid4().hex[:6].upper()}",
        original_filename="rag-test.txt",
        stored_filename="rag-test.txt",
        file_path="unused.txt",
        mime_type="text/plain",
        file_type=FileType.CHAT,
        size_bytes=100,
        sha256="a" * 64,
        status=EvidenceStatus.COMPLETED,
        processing_stage=ProcessingStage.COMPLETED,
        processing_progress=100,
        integrity_status=IntegrityStatus.VERIFIED,
        meta={"tags": ["rag-test"]},
        uploaded_at=utcnow(),
    )
    db.add(evidence)
    db.flush()
    content = ExtractedContent(
        evidence_id=evidence.id,
        kind=ContentKind.TEXT,
        text="The transfer of INR 18,50,000 was completed on 11 November 2026.",
    )
    db.add(content)
    db.flush()
    relevant = DocumentChunk(
        evidence_id=evidence.id,
        content_id=content.id,
        chunk_index=0,
        text="The transfer of INR 18,50,000 was completed on 11 November 2026.",
        content_kind="text",
        content_hash="b" * 64,
        embedding=[1.0, 0.0, 0.0],
        embedding_model="test-embedding",
        embedding_dim=3,
    )
    unrelated = DocumentChunk(
        evidence_id=evidence.id,
        content_id=content.id,
        chunk_index=1,
        text="A parking lot photograph contains three unidentified people.",
        content_kind="text",
        content_hash="c" * 64,
        embedding=[0.0, 1.0, 0.0],
        embedding_model="test-embedding",
        embedding_dim=3,
    )
    db.add_all([relevant, unrelated])
    db.commit()
    payload = {"evidence_id": evidence.id, "chunk_ids": [relevant.id, unrelated.id], "db": db}
    yield payload
    db.rollback()
    db.delete(evidence)
    db.commit()
    db.close()


def test_hybrid_retrieval_prefers_semantic_match(rag_evidence, monkeypatch):
    db = rag_evidence["db"]
    monkeypatch.setattr(ai_service, "api_key", "test-key")
    monkeypatch.setattr(ai_service, "embed_query", lambda question: [1.0, 0.0, 0.0])
    result = retrieval_service.retrieve(
        db,
        "Where did the money go?",
        evidence_ids=[rag_evidence["evidence_id"]],
        limit=2,
    )
    assert result.mode == "hybrid"
    assert result.chunks
    assert result.chunks[0].chunk.id == rag_evidence["chunk_ids"][0]


def test_assistant_falls_back_only_when_unavailable(rag_evidence, monkeypatch):
    db = rag_evidence["db"]
    monkeypatch.setattr(ai_service, "api_key", "test-key")
    monkeypatch.setattr(ai_service, "embed_query", lambda question: [1.0, 0.0, 0.0])
    monkeypatch.setattr(
        ai_service,
        "generate_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(AIServiceUnavailable("connection refused")),
    )
    response = assistant_service.answer_question(
        db,
        question="What happened with the transfer?",
        evidence_ids=[rag_evidence["evidence_id"]],
    )
    assert response.mode == "extractive"
    assert response.sources
    assert any("unavailable" in limitation for limitation in response.limitations)


def test_assistant_does_not_fallback_on_malformed_response(rag_evidence, monkeypatch):
    db = rag_evidence["db"]
    monkeypatch.setattr(ai_service, "api_key", "test-key")
    monkeypatch.setattr(ai_service, "embed_query", lambda question: [1.0, 0.0, 0.0])
    monkeypatch.setattr(
        ai_service,
        "generate_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(AIInvalidResponse("invalid JSON")),
    )
    with pytest.raises(AIInvalidResponse):
        assistant_service.answer_question(
            db,
            question="What happened with the transfer?",
            evidence_ids=[rag_evidence["evidence_id"]],
        )


def test_irrelevant_question_is_not_evidence_backed(rag_evidence, monkeypatch):
    db = rag_evidence["db"]
    monkeypatch.setattr(ai_service, "api_key", "test-key")
    monkeypatch.setattr(ai_service, "embed_query", lambda question: [0.0, 0.0, 1.0])
    result = retrieval_service.retrieve(
        db,
        "What is the capital of Finland?",
        evidence_ids=[rag_evidence["evidence_id"]],
        limit=3,
    )
    assert result.chunks == []


def test_assistant_gemini_answer_uses_retrieved_context(rag_evidence, monkeypatch):
    db = rag_evidence["db"]
    monkeypatch.setattr(ai_service, "api_key", "test-key")
    monkeypatch.setattr(ai_service, "embed_query", lambda question: [1.0, 0.0, 0.0])
    monkeypatch.setattr(
        ai_service,
        "generate_json",
        lambda *args, **kwargs: {
            "answer": "INR 18,50,000 was transferred on 11 November 2026 [S1].",
            "used_sources": [1],
            "insufficient_evidence": False,
            "limitations": [],
        },
    )
    response = assistant_service.answer_question(
        db,
        question="What happened with the transfer?",
        evidence_ids=[rag_evidence["evidence_id"]],
    )
    assert response.mode == "gemini"
    assert response.retrieval_mode == "hybrid"
    assert response.sources
    assert response.sources[0].evidence_id == rag_evidence["evidence_id"]
