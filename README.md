# TraceVault — Digital Evidence Intelligence

A full-stack digital-evidence platform for investigating incidents from screenshots, PDFs, chat exports, audio and video. It preserves originals with SHA-256, extracts text and speech, resolves people/places/entities, rebuilds a timeline, answers questions with citations, and produces court-ready reports on a hash-chained audit ledger.

TraceVault is the platform name; the React interface ships under the **Veritas** product mark.

---

## Highlights

- **Immutable evidence vault** — every upload is hashed at intake (SHA-256), stored read-only, and tracked on a tamper-evident audit ledger.
- **Multimodal extraction** — EasyOCR/Gemini vision for images, PyMuPDF + OCR for scanned PDFs, Whisper for audio, FFmpeg frame sampling + OCR + audio transcription for video.
- **Capture metadata** — record date, time, location, people and a note when adding evidence. Leave fields blank and the backend **auto-detects** them from the file after processing. Everything is editable later.
- **Entities & connections** — people, locations, organisations, phones, emails and dates, with a relationship graph built from evidence co-occurrence. Capture details are synced into entities and the timeline.
- **Timeline** — reconstructed events with raw timestamps, UTC normalisation, uncertainty flags and source locators (page, frame, audio segment).
- **Grounded assistant** — retrieval-augmented Q&A over preserved evidence with `[S1]`-style citations; deterministic metadata answers for questions like *"what is the latest evidence?"*.
- **Workspaces** — keep separate investigations isolated. Create, rename or delete workspaces from the sidebar; evidence, entities, timeline, reports and audit entries are scoped to the selected workspace.
- **Reports** — structured reports with an integrity section, stored server-side and exportable as PDF.
- **Audit ledger** — append-only, hash-chained log of every upload, view, download, query, edit, report and verification.

---

## Architecture

```
┌─────────────────────────────┐        HTTP (JSON, camelCase)
│  React 19 + TypeScript      │  ───────────────────────────────┐
│  Vite + Tailwind + Radix    │                                 │
│  React Flow · Recharts      │                                 ▼
└─────────────────────────────┘                     ┌─────────────────────────┐
                                                    │ FastAPI + SQLAlchemy    │
                                                    │ SQLite (dev) / Postgres │
                                                    │ Alembic migrations      │
                                                    └──────────┬──────────────┘
                                                               │
              ┌────────────────────────────┬───────────────────┼────────────────────┐
              ▼                            ▼                   ▼                    ▼
      OCR / PDF / Whisper          RAG index (chunks)     AI provider        Audit ledger
      FFmpeg (frames/audio)        lexical + embeddings   OpenCode / Gemini  hash chain
```

The frontend talks only to the backend. There is no local demo data: every list, graph, timeline event, dashboard figure and audit row comes from the API.

---

## Repository layout

```
.
├── frontend/                    React 19 + TypeScript + Vite UI
│   ├── src/
│   │   ├── components/          layout, evidence drawer/preview, UI primitives
│   │   ├── pages/               dashboard, vault, timeline, people, assistant, reports, audit, settings
│   │   ├── store/               app state + API loading (evidence, people, events, chat, audit)
│   │   ├── data/types.ts        shared UI types
│   │   └── lib/                 API client, formatting, workspace labels
│   └── vite.config.ts           dev proxy: /api → http://localhost:8000
├── backend/                     FastAPI + SQLAlchemy evidence service
│   ├── app/
│   │   ├── models/ schemas/ routers/ services/ middleware/ utils/
│   │   ├── main.py config.py database.py
│   ├── alembic/                 database migrations
│   ├── tests/                   end-to-end API tests
│   ├── uploads/                 preserved originals + derived artifacts (runtime)
│   └── README.md                backend setup, configuration, API reference
├── docs/
│   └── FRONTEND_INTEGRATION.md  implemented API ↔ UI field mapping
└── README.md
```

---

## Quick start

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.12+ | Torch/Whisper/Paddle wheels are built for 3.12 |
| Node 18+ | Frontend tooling |
| FFmpeg + ffprobe | Required for audio/video. Windows: `winget install Gyan.FFmpeg`; macOS: `brew install ffmpeg`; Debian: `apt install ffmpeg` |

### 1. Backend

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
python -m spacy download en_core_web_sm   # optional NER; AI extraction still works

copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux

uvicorn app.main:app --reload --port 8000
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health / capability report: <http://127.0.0.1:8000/api/health>
- Default database: SQLite at `backend/tracevault.db`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Sign in with the seeded local account:

```
aarav.shah@kestrel.legal
tracevault
```

You can also create a new account from the sign-in screen. Sign out from the account menu (top right).

> **Restart the dev server** after changing `vite.config.ts`; the proxy is loaded at startup.

### Production / preview

Build once and serve `frontend/dist`:

```bash
cd frontend
npm run build
```

Set `VITE_API_URL` in `frontend/.env.local` before building if the API is on another origin.

If the UI is served from a different origin than the API, set `VITE_API_URL` (e.g. in `frontend/.env.local`) before building, or reverse-proxy `/api` to the backend. Backend CORS already allows localhost ports and any origins listed in `CORS_ORIGINS`.

---

## AI provider configuration

Chat answers and entity extraction use one of two providers. Embeddings are **only** available through Google Gemini.

### Option A — Google Gemini (default)

```env
AI_PROVIDER=google
GEMINI_API_KEY=<your Google AI Studio key>
GEMINI_MODEL=gemini-2.5-flash
```

### Option B — OpenCode inference gateway

```env
AI_PROVIDER=opencode
OPENCODE_API_KEY=<your OpenCode Console key>
OPENCODE_MODEL=deepseek-v4.1-flash
# Go subscription:
OPENCODE_CHAT_BASE=https://opencode.ai/inference/go
# or pay-as-you-go Console balance:
# OPENCODE_CHAT_BASE=https://opencode.ai/inference
```

The API shape is chosen automatically from the model: Gemini models use `/google/v1beta`, all others use `/openai/v1`. Available models and pricing: <https://opencode.ai/inference/v1/models> and the OpenCode Console.

### Embeddings (optional)

Vector retrieval needs a Google key even when chat runs through OpenCode:

```env
GEMINI_API_KEY=<Google key>
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSIONS=768
```

Without it, evidence is still chunked and searchable via **lexical retrieval**; the assistant says so in its `retrievalMode`/limitations. Re-run `POST /api/assistant/reindex` after adding or changing the embedding model.

### Behaviour when the provider fails

- Not configured / unreachable / rate-limited / invalid model / insufficient balance → answers degrade to **extractive mode** (verbatim evidence excerpts) with an explicit limitation; the API still returns `200`.
- Malformed AI JSON after retries → **error envelope** (never silently presented as analysis).
- Questions about the vault itself ("latest evidence", "how many files") are answered deterministically from metadata (`mode: "metadata"`).

---

## Using the app

1. **Vault → Upload evidence.** Choose files (or drag them in). A dialog asks for date, time, location, people and a note; every field is optional. "Auto-detect missing details from the file" is on by default.
2. **Processing.** The backend hashes the original, extracts text/speech, indexes chunks, extracts entities and builds timeline events. The UI polls status and updates the row live.
3. **Review.** Open an item to see its real extracted text, capture details (marked *auto-detected* where applicable), integrity hash and linked people/events. Use **Edit details** to correct date/location/people — this re-syncs the graph and timeline.
4. **Explore.** Timeline and People & Connections update from the backend. Capture details become entities and a timeline event.
5. **Ask.** The assistant answers only from preserved evidence and cites sources. Anonymous or unrelated questions are rejected as insufficient evidence.
6. **Report.** Generate a report (stored server-side), then export the PDF.
7. **Audit.** Every action is in the chained ledger; `GET /api/audit/verify` recomputes it.

### Upload capture metadata

`POST /api/evidence/upload` accepts optional multipart fields alongside `files`:

| Field | Meaning |
|---|---|
| `date` | `YYYY-MM-DD` |
| `time` | `HH:MM` |
| `location` | free text (e.g. "Hotel Sunrise, Pune") |
| `persons` | JSON array of names |
| `note` | analyst note |
| `autoDetect` | `true`/`false` — fill blank fields from the file after processing |

Corrections after upload: `PATCH /api/evidence/{id}/capture` with the same `date`/`time`/`location`/`persons`/`note` fields.

### Media processing

| Media | What happens |
|---|---|
| Images | Pillow/EXIF metadata + OCR (EasyOCR, PaddleOCR, Tesseract or Gemini vision) |
| PDFs | PyMuPDF per-page text; image-only pages rendered and OCR'd; page numbers kept |
| Audio | FFmpeg → 16 kHz mono WAV → Whisper transcript with segment timestamps |
| Video | Frames sampled every `VIDEO_FRAME_INTERVAL_SECONDS` (default 8s, max `MAX_VIDEO_FRAMES`) + OCR per frame; audio track transcribed |

Tuning knobs: `VIDEO_FRAME_INTERVAL_SECONDS`, `MAX_VIDEO_FRAMES`, `WHISPER_MODEL`, `MAX_PDF_OCR_PAGES`, `OCR_ENGINE`, `OCR_LANGUAGES`. Reprocess after changes with `POST /api/evidence/{id}/reprocess`.

---

## API summary

Base URL: `http://127.0.0.1:8000/api` — full reference in [backend/README.md](backend/README.md) and Swagger.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Sign in with email/password → bearer token |
| POST | `/auth/register` | Create an account → bearer token |
| POST | `/auth/logout` | Revoke the current session |
| GET | `/auth/me` | Current user |
| GET | `/workspaces` | List workspaces with evidence counts |
| POST | `/workspaces` | Create a workspace |
| PATCH | `/workspaces/{id}` | Rename a workspace |
| DELETE | `/workspaces/{id}` | Delete (evidence/reports/audit move to the default workspace) |
| POST | `/evidence/upload` | Upload files with optional capture metadata |
| GET | `/evidence` | List/search/filter evidence |
| GET | `/evidence/{id}` | Detail: extracted content, entities, events, capture, duplicates |
| GET | `/evidence/{id}/status` | Processing progress/stage |
| GET | `/evidence/{id}/download` | Download original (audited) |
| PATCH | `/evidence/{id}/capture` | Correct capture details; re-sync graph + timeline |
| POST | `/evidence/{id}/verify` | Recompute SHA-256 |
| POST | `/evidence/{id}/reprocess` | Re-run extraction |
| DELETE | `/evidence/{id}` | Soft delete (original retained) |
| GET | `/timeline` | Reconstructed events with filters |
| GET | `/entities` · `/entities/graph` | Entities and relationship graph |
| POST | `/assistant/chat` | Grounded Q&A with citations |
| POST | `/assistant/reindex` | Backfill chunks/embeddings |
| POST | `/reports/generate` | Generate a report |
| GET | `/reports` · `/reports/{id}/pdf` | List / export |
| GET | `/audit` · `/audit/verify` | Ledger and chain verification |
| GET | `/health` | DB, storage and processor capabilities |

All responses are camelCase with UTC timestamps (`Z`). Errors share one envelope:

```json
{ "error": { "code": "…", "message": "…", "details": {}, "requestId": "…" } }
```

**Workspace scoping:** send `X-Workspace-Id: <workspace-uuid>` on every request (the UI does this automatically). Missing or unknown IDs fall back to the default workspace. Evidence, entities, timeline, assistant, reports and audit are all filtered by that workspace.

**Authentication:** the UI signs in via `/auth/login` and sends `Authorization: Bearer <token>` on every request. Sessions are opaque tokens stored hashed in `auth_sessions` and expire after `AUTH_SESSION_DAYS`. `AUTH_REQUIRED=true` enforces auth on the API; the default (`false`) keeps Swagger usable for local testing. The seeded account is `aarav.shah@kestrel.legal` / `DEFAULT_PASSWORD` (`tracevault`).

---

## Configuration (backend `.env`)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | SQLite file | Postgres: `postgresql+psycopg://user:pass@host/db` |
| `AUTO_CREATE_TABLES` | `true` | Prefer migrations + `false` in production |
| `UPLOAD_DIR` | `./uploads` | Originals, derived artifacts, temp |
| `MAX_UPLOAD_MB` | `2048` | Enforced while streaming |
| `CORS_ORIGINS` | localhost:5173/4173 | Any localhost port is also allowed |
| `AUTH_REQUIRED` | `false` | Enforce bearer-token auth on the API |
| `AUTH_SESSION_DAYS` | `7` | Session lifetime |
| `DEFAULT_PASSWORD` | `tracevault` | Password for the seeded analyst account |
| `AI_PROVIDER` | `google` | `google` or `opencode` |
| `GEMINI_API_KEY` | empty | Chat (google) **and** embeddings |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Google chat model |
| `OPENCODE_API_KEY` | empty | OpenCode Console key |
| `OPENCODE_MODEL` | `deepseek-v4.1-flash` | Any model from the gateway catalog |
| `OPENCODE_CHAT_BASE` | `https://opencode.ai/inference/go` | Go subscription root; use `…/inference` for Console balance |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Retrieval embeddings |
| `RAG_ENABLED` | `true` | Chunking + retrieval |
| `RAG_CHUNK_SIZE` / `OVERLAP` | `1200` / `150` | Characters per chunk |
| `OCR_ENGINE` | `auto` | auto/easyocr/paddleocr/tesseract/gemini/none |
| `OCR_LANGUAGES` | `en` | EasyOCR languages |
| `WHISPER_MODEL` | `small` | tiny/base/small/medium/large |
| `VIDEO_FRAME_INTERVAL_SECONDS` | `8` | Frame sampling interval |
| `MAX_VIDEO_FRAMES` | `12` | OCR cost cap |
| `MAX_PDF_OCR_PAGES` | `40` | OCR budget for scanned PDFs |
| `READ_ONLY_ORIGINALS` | `true` | Marks preserved files read-only |

**Restart the backend after changing `.env`** — settings are loaded at startup.

---

## Testing

```bash
cd backend
.venv\Scripts\python -m pytest -q      # end-to-end API suite

cd ../frontend
npm run build                          # tsc + production bundle
```

The backend suite exercises upload → hash → extraction → chunking → entity extraction → timeline → duplicate warnings → assistant retrieval/fallback → report + PDF → audit chain → soft delete, on isolated SQLite/uploads directories.

---

## Security & limitations

- **Authentication exists but is opt-in.** The UI signs in with bearer tokens (`auth_sessions`); set `AUTH_REQUIRED=true` to enforce auth on every API route. Without it, the API trusts local callers.
- Originals are immutable and read-only; deletion is a soft delete that retains the original for custody.
- The audit chain assumes a single API worker; scale with a dedicated ledger writer.
- OCR/ASR is CPU-bound. HD images and video can take tens of seconds; tune frame interval and model size for demos.
- Embeddings are ranked in Python over up to `RAG_MAX_CHUNKS` rows; move to pgvector for large corpora.
- OCR defaults to English (`OCR_LANGUAGES=en`); EasyOCR supports more languages.
- AI output is assistive, not evidence. Verify before disclosure; the UI labels extractive/auto-detected content.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Assistant always returns "AI synthesis is unavailable" | Provider key missing, invalid, out of balance, or model unavailable. Check the limitation text, then `/api/health` and your provider console. |
| `Insufficient balance` / `Model is unavailable` | Top up the Console balance or use a Go subscription + a model from the Go catalog; verify `OPENCODE_CHAT_BASE` and `OPENCODE_MODEL`. |
| Retrieval is lexical only | `GEMINI_API_KEY` is empty — embeddings require Google. Reindex after adding it. |
| Upload/download/chat fails in the UI but works in Swagger | Vite proxy not loaded (restart `npm run dev`) or UI served from a different origin without `VITE_API_URL`. |
| Changes to `.env` have no effect | Restart `uvicorn`; settings are read at startup. |
| Video produced little text | Short/silent clip or sparse frames — lower `VIDEO_FRAME_INTERVAL_SECONDS` and reprocess. |
| OCR/Whisper first run is slow | Models download weights on first use (EasyOCR ~100 MB, Whisper small ~460 MB). |

---

## License / attribution

Hackathon project. Third-party models and services (EasyOCR, Whisper, PyMuPDF, FFmpeg, Google Gemini, OpenCode) are subject to their own licenses and terms.
