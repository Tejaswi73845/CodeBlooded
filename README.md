# TraceVault — Digital Evidence Intelligence

A full-stack hackathon application for preserving digital evidence, extracting facts from screenshots/PDFs/audio/video, resolving entities, reconstructing an incident timeline and answering questions with evidence citations.

TraceVault is the platform name; the React interface ships under the in-app **Veritas** product mark.

## Repository layout

```
.
├── frontend/                 React 19 + TypeScript + Vite UI
│   ├── src/
│   │   ├── components/       layout, evidence, UI primitives
│   │   ├── pages/            dashboard, vault, timeline, people, assistant, reports, audit, settings
│   │   ├── store/            app state (evidence, uploads, chat, theme, toasts)
│   │   ├── data/             typed demo data
│   │   └── lib/              API seam, formatting, assistant mock
│   ├── public/
│   ├── package.json
│   └── README.md
├── backend/                  FastAPI + SQLAlchemy evidence intelligence service
│   ├── app/
│   │   ├── models/           SQLAlchemy models
│   │   ├── schemas/          camelCase API contracts
│   │   ├── routers/          evidence, timeline, entities, assistant, reports, audit, health
│   │   ├── services/         OCR, PDF, audio, video, entities, timeline, AI, integrity, audit
│   │   ├── middleware/
│   │   └── utils/
│   ├── alembic/              database migrations
│   ├── tests/                end-to-end API tests
│   ├── uploads/              preserved originals + derived artifacts (runtime)
│   ├── requirements.txt
│   ├── docker-compose.yml
│   ├── README.md             backend setup, API and architecture
├── docs/
│   └── FRONTEND_INTEGRATION.md  API-to-UI field mapping and wiring guide
├── .agents/                  local agent skills (tooling, not part of the app)
└── skills-lock.json
```

## Quick start

### 1. Backend

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Requires Python 3.12+ and FFmpeg. Without a Gemini key the service uses deterministic extraction and extractive answers; every fallback is labelled. Swagger: <http://127.0.0.1:8000/docs>.

See [backend/README.md](backend/README.md) for PostgreSQL/Alembic, configuration and the full API.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The UI currently runs against its typed demo data; the API integration contract and wiring guide are in [docs/FRONTEND_INTEGRATION.md](docs/FRONTEND_INTEGRATION.md).

## Main workflow

1. Upload a screenshot, PDF, audio or video file.
2. The backend hashes the original, extracts text/transcripts (OCR, PyMuPDF, Whisper), and resolves people, phone numbers, emails, organizations, locations and dates.
3. Timeline events are reconstructed with source evidence and uncertainty flags.
4. Ask grounded questions; responses cite the preserved evidence and page/audio/frame timestamps.
5. Generate a structured report with an integrity section and export it as PDF.
6. Verify the append-only audit chain.

## Design notes

- Originals are immutable; derived artifacts are stored separately.
- Gemini keys live only on the server. Text extraction and entity fallbacks never invent missing values.
- The assistant uses hybrid semantic retrieval (Gemini embeddings + lexical + entity ranking); extractive fallback appears only when Gemini is unavailable, never as a silent substitute for malformed AI output.
- The backend contract is camelCase and UTC (`Z`) so it can replace the frontend mock store without redesigning components.
