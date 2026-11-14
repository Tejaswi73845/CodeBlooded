# TraceVault — Backend

FastAPI backend for the TraceVault digital evidence platform. It preserves original files, extracts text and speech, resolves entities, reconstructs a timeline and answers questions with citations back to the preserved source.

Everything runs locally. Gemini, OCR and Whisper degrade explicitly when unavailable — the API never fabricates extracted content.

Frontend wiring guide: [`../docs/FRONTEND_INTEGRATION.md`](../docs/FRONTEND_INTEGRATION.md).

## What is implemented

| Priority | Capability | Status |
|---|---|---|
| P0 | Multi-file upload, immutable storage, SHA-256 at intake | ✅ |
| P0 | Image OCR (EasyOCR, optional Paddle/Tesseract/Gemini vision) | ✅ |
| P0 | PDF text extraction with page numbers and scanned-page OCR | ✅ |
| P0 | Audio transcription with Whisper and segment timestamps | ✅ |
| P0 | Gemini entity extraction + deterministic spaCy/regex fallback | ✅ |
| P0 | Timeline reconstruction with UTC normalisation and uncertainty flags | ✅ |
| P1 | Video frame extraction, frame OCR, audio track transcription | ✅ |
| P1 | Evidence-grounded assistant with hybrid RAG, page/audio citations | ✅ |
| P1 | Semantic chunk index + Gemini embeddings (`gemini-embedding-001`) | ✅ |
| P1 | Entity relationship graph | ✅ |
| P1 | Exact SHA-256 + perceptual (dHash) duplicate warnings | ✅ |
| P2 | Review findings (integrity, duplicates, uncertain timestamps) | ✅ |
| P2 | Server-side PDF report export | ✅ |
| P2 | Hash-chained, append-only audit ledger + verification endpoint | ✅ |

Original uploads are stored read-only and are never rewritten. Derived artifacts (audio, PDF page renders, video frames) live under a separate `derived/` tree.

## Architecture

```
backend/
  app/
    main.py              FastAPI app, CORS, lifespan, error envelopes
    config.py            pydantic-settings (env driven)
    database.py          SQLAlchemy engine/session + SQLite WAL fallback
    models/              User, Evidence, ExtractedContent, Entity,
                         EntityRelationship, TimelineEvent, AuditLog, Report
    schemas/             camelCase API contracts
    routers/             evidence, timeline, entities, assistant, reports, audit, health
    services/
      file_service       upload streaming, validation, SHA-256, storage
      ocr_service        EasyOCR / PaddleOCR / Tesseract / Gemini vision
      pdf_service        PyMuPDF text + scanned page OCR
      audio_service      FFmpeg probe/convert + Whisper transcription
      video_service      representative frames + audio extraction
      entity_service     Gemini extraction, validated entities, fallback NER
      chunking_service   locator-preserving evidence chunks for retrieval
      rag_service        chunk persistence + Gemini embedding index
      retrieval_service  hybrid vector/lexical/entity ranking
      timeline_service   event extraction, normalisation, dedupe
      assistant_service  retrieval + Gemini answer with citations
      report_service     structured report + ReportLab PDF
      integrity_service  re-hash and verify originals
      audit_service      previous-hash chaining
      pipeline_service   asynchronous orchestration
    middleware/          request IDs + structured request logging
    utils/               file safety, time parsing, text, logging
  alembic/               migration environment + initial schema
  tests/                 real end-to-end workflow tests
  uploads/               originals + derived artifacts (created at runtime)
```

## Quick start (SQLite, no infrastructure)

Requirements: Python **3.12+**, FFmpeg on PATH. EasyOCR/Whisper download model weights on first use.

```bash
cd backend

# Python 3.12 specifically (Paddle/Torch/Whisper wheels)
py -3.12 -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
python -m spacy download en_core_web_sm

copy .env.example .env            # Windows
# cp .env.example .env            # macOS/Linux

uvicorn app.main:app --reload --port 8000
```

* Swagger UI: <http://127.0.0.1:8000/docs>
* Health: <http://127.0.0.1:8000/api/health>
* OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

Defaults use SQLite at `backend/tracevault.db`. This is a development convenience; production uses PostgreSQL.

### FFmpeg

Install and ensure `ffmpeg` / `ffprobe` are on PATH (Windows: `winget install Gyan.FFmpeg`, macOS: `brew install ffmpeg`, Debian: `apt install ffmpeg`). On Windows, TraceVault also resolves the WinGet package location automatically.

### Model downloads

* EasyOCR: detection + recognition weights (~100 MB) download on first OCR call.
* Whisper: `small` (~460 MB) downloads on first transcription. For a fast demo set `WHISPER_MODEL=tiny` or `DEMO_AUDIO_MODEL=true`.
* spaCy: `en_core_web_sm` (~13 MB) improves person/organisation recall. Without it, a conservative regex fallback is used.
* Gemini: optional. Set `GEMINI_API_KEY` to enable AI analysis. Without it, entity extraction uses deterministic NER and the assistant returns an extractive summary (clearly labelled).

## PostgreSQL + Alembic

```bash
docker compose up -d db
cp .env.example .env
# .env:
# DATABASE_URL=postgresql+psycopg://tracevault:tracevault@localhost:5432/tracevault
# AUTO_CREATE_TABLES=false

alembic upgrade head
uvicorn app.main:app --port 8000
```

`AUTO_CREATE_TABLES=true` (the default) creates tables on startup for hackathon speed. With Postgres, prefer `AUTO_CREATE_TABLES=false` and run migrations. The initial Alembic migration lives in `alembic/versions/`.

## Configuration

All settings are in `.env.example`. Important values:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | SQLite file | Postgres: `postgresql+psycopg://user:pass@host/db` |
| `UPLOAD_DIR` | `./uploads` | Originals/derived/temp |
| `MAX_UPLOAD_MB` | `2048` | Enforced while streaming |
| `CORS_ORIGINS` | localhost:5173, … | Comma-separated; also allows any localhost port |
| `GEMINI_API_KEY` | empty | Server-side only; never exposed |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Answer generation model |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Retrieval embeddings |
| `GEMINI_EMBEDDING_DIMENSIONS` | `768` | Stored vectors are 768-dimensional |
| `RAG_CHUNK_SIZE` | `1200` | Characters per retrieval passage |
| `RAG_MIN_VECTOR_MATCH` | `0.52` | Prevents unrelated questions becoming evidence-backed |
| `OCR_ENGINE` | `auto` | auto/easyocr/paddleocr/tesseract/gemini/none |
| `WHISPER_MODEL` | `small` | tiny/base/small/medium/large |
| `VIDEO_FRAME_INTERVAL_SECONDS` | `8` | Frames sampled across a video |
| `MAX_VIDEO_FRAMES` | `12` | OCR cost cap |
| `MAX_PDF_OCR_PAGES` | `40` | OCR budget for scanned PDFs |
| `READ_ONLY_ORIGINALS` | `true` | Marks preserved files read-only |

## Processing model

`POST /api/evidence/upload` streams and hashes each file, stores it, records an audit entry, returns **202** and schedules a background job. Poll `GET /api/evidence/{id}/status` for `progress`, `stage` and `error`.

```
pending → processing → completed
                     ↘ failed (error message preserved)
```

Stages: `text_extraction`, `audio_transcription`, `rag_indexing`, `entity_extraction`, `timeline_reconstruction`, `integrity_check`.

Processing is serialised in-process with a lock because OCR/ASR models are CPU- and memory-heavy. For multiple workers, replace `BackgroundTasks` with a real queue (RQ/Celery/Arq). Interrupted jobs are marked `failed` on startup and can be retried with `POST /api/evidence/{id}/reprocess`.

### Extraction detail

* **Images** — Pillow metadata/EXIF, EasyOCR blocks with confidence and bounding boxes.
* **PDFs** — PyMuPDF per-page text; image-only pages are rendered at 2× and OCR'd; page numbers preserved.
* **Audio** — FFmpeg → 16 kHz mono WAV → Whisper segments (start/end/confidence).
* **Video** — representative frames every N seconds → OCR with frame timestamps; audio track → Whisper with timestamps. Frame-derived text and transcripts are stored separately.
* **Text/chat/data** — UTF-8/CP1252 decoding, truncation at 5 MB for analysis (original preserved).

### Entities and timeline

With Gemini configured, extraction is schema-constrained and every item must carry a verbatim excerpt that is present in the source text. Anything that cannot be verified is discarded. Without Gemini, spaCy NER + regex extracts people, phones, emails, organisations, locations and dates, all labelled `source: "spacy"` or `"regex_fallback"`.

Timeline events keep:

* `at` — normalised UTC timestamp (nullable, ISO with `Z`)
* `atRaw` — timestamp exactly as written
* `timeUncertain` — true when the source gives no explicit time
* `evidenceId` + `confidence` + `pageNumber` / `sourceTimestamp` / `sourceExcerpt`

Uncertainty is never silently upgraded to a precise timestamp.

## API

Base URL: `http://127.0.0.1:8000/api`

| Method | Path | Purpose |
|---|---|---|
| POST | `/evidence/upload` | Multipart `files` (or `file`); 202 with items/warnings |
| GET | `/evidence` | Search/filter (`q`, `type`, `status`, `personId`, `sort`, pagination) |
| GET | `/evidence/{id}` | Metadata, extracted content, entities, events, duplicates |
| GET | `/evidence/{id}/status` | Live processing progress |
| GET | `/evidence/{id}/download` | Original file; logs access; exposes `X-Evidence-SHA256` |
| POST | `/evidence/{id}/verify` | Recompute SHA-256, update integrity, audit |
| POST | `/evidence/{id}/reprocess` | Re-run extraction |
| DELETE | `/evidence/{id}` | Soft delete; original retained; audited |
| GET | `/timeline` | `from`, `to`, `personId`, `category`, `uncertain`, `q` |
| GET | `/timeline/{id}` | Single event with source evidence |
| GET | `/entities` | `type`, `q`, `evidenceId` |
| GET | `/entities/graph` | Nodes/edges for the relationship UI |
| GET | `/entities/{id}` | Evidence refs, related entities, events |
| POST | `/assistant/chat` | Hybrid RAG Q&A with citations |
| POST | `/assistant/reindex` | Backfill chunks + embeddings for existing evidence |
| POST | `/reports/generate` | Build structured report |
| GET | `/reports` | Saved reports |
| GET | `/reports/{id}` | Report JSON + markdown |
| GET | `/reports/{id}/pdf` | Server-rendered PDF |
| GET | `/audit` | Filterable ledger with chain validity |
| GET | `/audit/verify` | Recompute the hash chain |
| GET | `/health` | DB/storage/processor capability report |

All responses use camelCase and UTC timestamps with `Z` (the frontend's dialect). Errors have one shape:

```json
{ "error": { "code": "unsupported_media_type", "message": "…", "details": {}, "requestId": "…" } }
```

### Demo requests

```bash
curl -F "files=@incident.pdf" http://127.0.0.1:8000/api/evidence/upload

curl http://127.0.0.1:8000/api/evidence
curl http://127.0.0.1:8000/api/evidence/<id>
curl http://127.0.0.1:8000/api/evidence/<id>/status

curl "http://127.0.0.1:8000/api/timeline?personId=<entity-uuid>"
curl http://127.0.0.1:8000/api/entities/graph

curl -X POST http://127.0.0.1:8000/api/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What happened on 10 November 2026?","limit":6}'

curl -X POST http://127.0.0.1:8000/api/assistant/reindex \
  -H "Content-Type: application/json" \
  -d '{}'

curl -X POST http://127.0.0.1:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"title":"Incident Summary","reportType":"incident"}'

curl http://127.0.0.1:8000/api/audit/verify
```

Optional actor attribution on any request: `X-Actor: Investigator Name`. The default analyst is seeded automatically.

## Assistant grounding (RAG)

Every evidence item is chunked into locator-aware passages (`page`, audio/frame timestamps) during processing. Chunks are embedded with Gemini `gemini-embedding-001` at 768 dimensions and stored in `document_chunks` (portable JSON vectors, no pgvector requirement).

At question time:

1. The question is embedded with `RETRIEVAL_QUERY`.
2. Retrieval combines cosine similarity (70%), lexical score (20%) and explicit entity matches (10%).
3. Irrelevant questions are rejected by a vector-relevance gate rather than answered from unrelated evidence.
4. Top passages are passed to Gemini with source markers, evidence IDs and locators; returned citations are validated.

`GET /api/health` exposes chunk coverage. `POST /api/assistant/reindex` backfills the index for evidence processed before RAG was enabled. New uploads index automatically; if the embedding API is unavailable, chunks are still stored and can be re-embedded later.

### Fallback policy

* Gemini **not configured, unreachable, timed out, rate-limited (429) or 5xx** → `mode: "extractive"` with verbatim retrieved passages and an explicit limitation.
* Gemini returns **malformed JSON, blocks the request, or rejects the key/model** → HTTP 502/422 error envelope. The chatbot does **not** silently pretend an extractive answer is AI analysis.
* Query embedding unavailable but generation reachable → lexical retrieval, Gemini answer still runs (`retrievalMode: "lexical"`).
* No passage passes relevance → `insufficientEvidence: true`.
* Questions about the vault itself (“latest evidence”, “how many files”, “list recent uploads”) are answered deterministically from evidence metadata with `mode: "metadata"`; they do not depend on Gemini.

If the request includes `evidenceIds` and none match active evidence, the assistant returns an explicit insufficient-evidence message naming the filter rather than claiming the workspace is empty.

## Integrity and audit

* SHA-256 is computed while streaming, before the file is moved into place.
* Originals are marked read-only; duplicates are preserved, not deleted.
* Every upload, rejection, status transition, access, download, verification, reprocess, report and assistant query creates an audit row.
* Each row stores `previousHash` and its own `entryHash` computed over the previous hash, timestamp, actor, action, target, result and canonical details.
* `GET /api/audit/verify` recomputes the chain and reports the first broken entry.
* The append-only chain assumes a single API worker. For horizontal scaling use a Postgres advisory lock or a dedicated ledger writer.

## Security notes

* Extensions, MIME type and file signatures are validated; traversal is stripped from names.
* All storage paths resolve inside `UPLOAD_DIR`; downloads are served only by evidence ID.
* Upload size is enforced during streaming.
* Uploads are never served statically.
* No API keys are hardcoded; Gemini keys live only in the server environment.
* CORS is limited to configured origins plus localhost dev ports.
* There is **no authentication/RBAC** yet — add it before exposing the service publicly.

## Tests

```bash
pytest -q
```

The suite exercises a real PDF upload → hash → text extraction → RAG chunking → embedding interface (mocked in tests) → entity extraction → timeline → duplicate warning → assistant retrieval + fallback policy → report + PDF → audit chain verification → soft delete. It runs on isolated SQLite/uploads directories.

## Known limitations

* In-process background jobs and an in-process audit-chain lock; use a queue and a single ledger writer when scaling.
* OCR/ASR on CPU is slow (an HD screenshot can take ~30–60 s; video processing scales with sampled frames). Tune frame interval/model size.
* OCR is configured for English by default (`OCR_LANGUAGES=en`); EasyOCR supports more languages.
* The Gemini paths require a valid key. Without it, entity extraction keeps its labelled deterministic fallback, while the chatbot returns a labelled extractive response.
* Embeddings are ranked in Python over up to `RAG_MAX_CHUNKS` rows (portable SQLite/Postgres). Move to pgvector when the corpus grows beyond a few thousand chunks.
* Re-run `POST /api/assistant/reindex` after changing the embedding model/dimensions.
* ReportLab PDF layout is intentionally simple.
* No auth, case-level tenancy or rate limiting yet.
