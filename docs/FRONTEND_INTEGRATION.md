# Frontend ↔ Backend Contract (implemented)

The React app in `frontend/` is wired to the FastAPI backend. This document records the current request/response mapping and conventions. There is no mock dataset.

## Connection

- **Dev:** Vite proxies `/api` → `http://localhost:8000` (`VITE_BACKEND_URL` overrides the target).
- **Build/preview:** set `VITE_API_URL` (e.g. `http://host:8000`), or reverse-proxy `/api` to the backend.
- Backend CORS allows localhost ports plus anything in `CORS_ORIGINS`.
- All responses are camelCase; timestamps are UTC and end in `Z`.
- Errors use one envelope:

```json
{ "error": { "code": "…", "message": "…", "details": {}, "requestId": "…" } }
```

## Evidence

`GET /api/evidence` → `EvidenceItem` fields used by the UI:

| UI (`src/data/types.ts`) | Backend |
|---|---|
| `id` | `id` (UUID) |
| `name`, `type`, `mime`, `size` | same |
| `uploadedAt`, `uploadedBy`, `source` | same (UTC `Z`) |
| `hash` | `hash` (SHA-256) |
| `status` | backend `status` mapped: `pending → queued`, `processing`, `completed → processed`, `failed` |
| `integrity` | `verified \| pending \| mismatch` |
| `personIds` | array of backend entity UUIDs |
| `tags`, `note`, `preview`, `pages`, `duration` | same |
| `occurredAt`, `location`, `persons`, `captureNote`, `captureDetected` | capture metadata (+ which fields were auto-detected) |

`GET /api/evidence/{id}/status` → `{ status, stage, progress, error, integrity, verifiedAt }` (polled every 2 s while processing).

## Upload with capture metadata

`POST /api/evidence/upload` — `multipart/form-data`:

| Field | Type | Notes |
|---|---|---|
| `files` | file[] | one or more files |
| `date` | `YYYY-MM-DD` | optional |
| `time` | `HH:MM` | optional |
| `location` | string | optional |
| `persons` | JSON array string | e.g. `["Ravi Kulkarni"]` |
| `note` | string | optional |
| `autoDetect` | `"true"` / `"false"` | fill blank capture fields from the file after processing |

Response: `{ items: EvidenceSummary[], duplicates: [], errors: [], accepted: n }` (HTTP 202). Items are real backend records; the UI prepends the returned item and then polls status.

### Editing capture details

`PATCH /api/evidence/{id}/capture`:

```json
{ "date": "2026-11-11", "time": "09:00", "location": "Cafe Blue, Mumbai", "persons": ["Vikram Rao"], "note": "Corrected" }
```

Returns the updated `EvidenceSummary`. The backend replaces capture-derived entities/relationships/timeline event, so the connection graph and timeline refresh immediately.

## People and graph

`GET /api/entities?limit=300` → entities with `id`, `type`, `value`, `mentionCount`, `evidenceCount`, `evidenceIds`. The UI maps `type === "person"` to a `Person` node and connects people that share an evidence id.

## Timeline

`GET /api/timeline?limit=500` → `{ id, at, atRaw, timeUncertain, title, description, category, severity, confidence, evidenceId, evidenceIds, personIds, location, extractionSource }`. Mapped to the UI `IncidentEvent`; events without `at` are skipped.

## Assistant

`POST /api/assistant/chat`

```json
{ "question": "What happened at the meeting?", "limit": 8 }
```

Response fields used: `answer` (with `[S1]` citations), `sources[]` (`evidenceName`, `excerpt`, locator), `insufficientEvidence`, `mode`, `retrievalMode`, `model`, `limitations`. The UI renders limitations below the answer and turns `sources[].evidenceName` into citation chips.

`mode` values: `gemini` (AI synthesis), `extractive` (provider unavailable — labelled), `metadata` (deterministic vault questions), `insufficient`. Reindex after enabling embeddings: `POST /api/assistant/reindex` with `{ "evidenceIds": [] }`.

## Reports

- `GET /api/reports?limit=50` → saved reports (`id`, `title`, `type`, `status`, `author`, `createdAt`, `pages`, `evidenceCount`).
- `POST /api/reports/generate` → `{ title, reportType: "incident" | "chronology" | "integrity" | "relationships" | "custom", includeAiSummary }`.
- `GET /api/reports/{id}/pdf` → server-rendered PDF (downloaded as a blob; browser print is the fallback).

## Audit

`GET /api/audit?limit=300` → `{ items: [{ id, actor, action, target, at, ip, result }], total, chainValid }`. `GET /api/audit/verify` recomputes the hash chain.

## Implementation notes

- Browser hash computation is no longer used: the backend hashes at intake and returns the digest.
- Deleting an item removes it from the UI list; the backend keeps the original (soft delete) and records the action.
- The UI shows empty states when the backend has no data — there is no synthetic fallback.
