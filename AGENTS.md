# AGENTS.md

TraceVault is a React SPA in `frontend/` plus a FastAPI API in `backend/`. There is no root manifest or workspace tool — run every command from one subproject.

## Commands

Backend (from `backend/`):
- Setup: `py -3.12 -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`, `copy .env.example .env`
- Dev: `uvicorn app.main:app --reload --port 8000` → `/docs`, `/api/health`
- Tests: `.venv\Scripts\python -m pytest -q`
- One test: `.venv\Scripts\python -m pytest tests/test_rag.py::test_irrelevant_question_is_not_evidence_backed -q`
- Postgres path: `docker compose up -d db`, then `alembic upgrade head` (uses `DATABASE_URL`)

Frontend (from `frontend/`):
- `npm install`; `npm run dev` (port 5173)
- `npm run build` is the only frontend check (`tsc -b && vite build`; strict, `noUnusedLocals`/`noUnusedParameters`)
- No frontend test, lint, or format scripts exist.

- Use Node 20.19+ for Vite 7; the root README's "Node 18+" is stale.
- FFmpeg/ffprobe must be on PATH for audio/video. First OCR/Whisper run downloads weights.
- Seeded login: `aarav.shah@kestrel.legal` / `tracevault`.

## Config and runtime

- Settings are a module-level singleton (`app/config.py`) loaded at import. Restart `uvicorn` after `.env` edits; tests must set env before importing `app.main`.
- `AUTH_REQUIRED` defaults to `false`; auth middleware still runs, and anonymous callers act as the seeded demo user.
- Frontend `VITE_API_URL`: empty = same-origin. Dev proxies `/api` → `localhost:8000`; override with `VITE_BACKEND_URL`. Restart Vite after editing `vite.config.ts`. `VITE_API_URL` is baked at build time.
- `backend/tracevault.db`, `backend/uploads/`, and `.env` are gitignored runtime artifacts.

## Backend conventions

- Entry point: `app/main.py`. Routers are thin; logic lives in `app/services/`, and `pipeline_service` orchestrates upload → extraction → RAG → entities → timeline.
- Response/request schemas extend `APIModel` (`app/schemas/common.py`) for camelCase aliases and UTC `Z` datetimes. Keep SQLAlchemy model fields snake_case.
- Workspace isolation: user-data routes depend on `current_workspace` and filter every query by `workspace_id`. A header workspace owned by another user falls back to the caller's default; never leak across users.
- Audit: upload/view/download/verify/edit/query/report/delete must call `record_audit`, which chains `previousHash` → `entryHash`. Chain integrity assumes one worker.
- Errors: raise `AppError` so responses stay `{ "error": { code, message, details, requestId } }`.
- Uploads return 202 and process in `BackgroundTasks` under an in-process lock; the UI polls `/evidence/{id}/status` every 2s. Keep requests non-blocking for OCR/ASR.
- Originals are immutable; derived artifacts go to `uploads/derived/`. Deletes are soft.
- AI: chat through Gemini or OpenCode, embeddings only Gemini. Provider outage → `mode: "extractive"` with a limitation; malformed AI JSON → error. Do not turn provider failures into fabricated analysis.
- Model changes need an Alembic revision in `alembic/versions/`. `AUTO_CREATE_TABLES=true` plus `ensure_auth_schema`/`ensure_workspace_schema` are dev-only compatibility shims.

## Backend tests

- `tests/conftest.py` sets isolated SQLite/upload dirs, `OCR_ENGINE=none`, blank AI keys, then imports the app. New tests must preserve that import order.
- `client` is session-scoped and shares one temp DB; rows persist between tests. Do not assume an empty vault or stable counts.
- AI is never called: tests monkeypatch `ai_service`/embedding methods. No network or model downloads in tests.

## Frontend conventions

- All HTTP goes through `src/lib/api.ts`; there is no mock dataset. When the API is unavailable, show empty/error states rather than seed local data.
- `@/` alias → `src/` (configured in Vite and tsconfig). UI state/loading lives in `src/store/app-store.tsx`.
- Tailwind CSS v4 via `@tailwindcss/vite`; there is no `tailwind.config.*`. Design tokens and dark-mode variables live in `src/index.css`; primitives in `src/components/ui/` follow shadcn patterns.
- Backend statuses are mapped in `api.ts` (`pending→queued`, `completed→processed`); keep `docs/FRONTEND_INTEGRATION.md` in sync with API field changes.

## Docs

`README.md` (setup/config/troubleshooting), `backend/README.md` (API/processing), `frontend/README.md` (screens), `docs/FRONTEND_INTEGRATION.md` (field mapping). Code and config win when docs drift.
