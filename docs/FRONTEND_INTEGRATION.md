# Connecting the TraceVault frontend

The existing React app in `frontend/` is intentionally untouched. Its data lives in `frontend/src/store/app-store.tsx` with mock seed data in `frontend/src/data/mock.ts`. This document maps that UI onto the backend contract without redesigning anything.

## 1. Configure the API URL

Create `frontend/.env.local`:

```
VITE_API_URL=http://127.0.0.1:8000/api
```

Backend CORS already allows `http://localhost:5173`, `http://127.0.0.1:5173`, any localhost port, and additional origins from `CORS_ORIGINS`.

## 2. Field mapping

### Evidence — `GET /api/evidence`

The backend returns camelCase fields matching the frontend `EvidenceItem`:

| Frontend (`frontend/src/data/types.ts`) | Backend |
|---|---|
| `id` | `id` (UUID) |
| `name` | `name` |
| `type` (`image \| document \| audio \| video \| chat \| data`) | `type` (same values) |
| `mime` | `mime` |
| `size` | `size` |
| `uploadedAt` | `uploadedAt` (UTC, ends in `Z`) |
| `uploadedBy` | `uploadedBy` |
| `source` | `source` (`"Upload"`) |
| `hash` | `hash` (SHA-256) |
| `tags` | `tags` |
| `personIds` | `personIds` (backend entity UUIDs) |
| `eventIds` | `eventIds` |
| `duration` / `pages` / `preview` | same |
| `note` | `note` (extraction summary) |
| `duplicateOf` | `duplicateOf` |
| `integrity` | `integrity` (`verified \| pending \| mismatch`) |
| `status` | `status` |

Map the processing status for the existing badges:

```ts
const status = {
  pending: "queued",
  processing: "processing",
  completed: "processed",
  failed: "failed",
} as const;
```

`GET /api/evidence` also returns `counts` (per backend status) for dashboard cards, and `total`/`limit`/`offset`.

### People — `GET /api/entities?type=person`

Map an entity to the frontend `Person`:

```ts
{
  id: entity.id,
  name: entity.value,
  role: entity.type === "person" ? "Person of interest" : entity.type,
  initials: entity.value.split(/\s+/).map(v => v[0]).slice(0,2).join("").toUpperCase(),
  tint: "#5E5CE6",
  risk: "medium",             // no inferred risk; do not fabricate one
  phone: related phone entity, // optional, via /entities/{id}.relatedEntities
  email: related email entity,
  evidenceCount: entity.evidenceCount,
  lastSeen: entity.lastSeenAt,
  note: `Mentioned ${entity.mentionCount} times across ${entity.evidenceCount} evidence items.`,
}
```

Do not derive risk levels from AI guesses. If the UI needs risk, keep it analyst-assigned.

### Timeline — `GET /api/timeline`

Returns items with `at`, `atRaw`, `timeUncertain`, `title`, `description`, `category`, `severity`, `evidenceId`, `evidenceIds`, `evidenceName`, `personIds`, `people`, and page/timestamp locators. The frontend's `IncidentEvent` shape is a subset; add `evidenceIds` where the UI expects an array.

Filters are `from`, `to`, `personId`, `category`, `uncertain`, `q`. Person IDs are backend entity UUIDs (the same IDs present in evidence `personIds`).

### Audit — `GET /api/audit`

`{ items: [{ id, actor, action, target, at, ip, result, hash, previousHash }], total, chainValid }` maps directly to the existing audit table.

### Reporting — `POST /api/reports/generate`

The backend accepts:

```json
{
  "title": "Incident Summary — EV-2026-0142",
  "reportType": "incident",
  "includeAiSummary": true,
  "evidenceIds": []
}
```

It returns structured `content` (summary, findings, chronology, people, evidence, integrity, reviewItems) plus `markdown`. `GET /api/reports/{id}/pdf` returns a real server-rendered PDF. The current UI's print-to-PDF button can keep working or be pointed at this endpoint.

### Assistant — `POST /api/assistant/chat`

```json
{ "question": "What happened on 10 November?", "limit": 8 }
```

Response:

```json
{
  "answer": "…with [S1] citations…",
  "insufficientEvidence": false,
  "sources": [{
    "evidenceId": "…",
    "evidenceName": "chat_export.txt",
    "fileType": "chat",
    "excerpt": "…",
    "pageNumber": null,
    "timestampStart": 123.4,
    "timestampEnd": 130.2,
    "locator": "02:03–02:10",
    "relevance": 0.91
  }],
  "mode": "gemini",
  "retrievalMode": "hybrid",
  "chunksConsidered": 7,
  "limitations": [],
  "generatedAt": "2026-11-14T08:27:22Z"
}
```

Render `sources` as the citation chips. When `insufficientEvidence` is true, show the answer as the empty-state explanation, not as evidence.

`mode` is `gemini`, `extractive`, or `metadata`; `retrievalMode` is `hybrid`, `lexical`, or `metadata`. Metadata answers are deterministic lookups for questions such as “what is the latest evidence?”. Extractive is only used when Gemini is not configured or cannot be reached; show the limitation text. If Gemini is reachable but returns malformed output, the API returns a 502 error envelope rather than a silent extractive answer. Handle error responses with the shared `error.message` and `error.requestId` fields.

To backfill semantic search after enabling Gemini or switching embedding models:

```http
POST /api/assistant/reindex
Content-Type: application/json

{ "evidenceIds": [] }
```

## 3. Upload integration

The existing drag/drop and progress UI can use `XMLHttpRequest` for true upload progress:

```ts
export function uploadEvidence(files: File[], onProgress: (percent: number) => void) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    files.forEach(file => form.append("files", file));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${import.meta.env.VITE_API_URL}/evidence/upload`);
    xhr.upload.onprogress = e => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => xhr.status === 202 ? resolve(JSON.parse(xhr.responseText)) : reject(new Error(xhr.responseText));
    xhr.onerror = () => reject(new Error("Upload failed"));
    xhr.send(form);
  });
}
```

Returned items are already backend records. Poll each `GET /evidence/{id}/status` every 1–2 s and update the row/progress. The response `duplicates` array contains exact and perceptual matches — surface it as a warning; do not delete either file.

## 4. Suggested integration order

1. Replace `frontend/src/lib/api.ts` mock functions with fetch calls; keep the same signatures.
2. Load evidence in the store and poll incomplete items.
3. Replace the assistant mock in `frontend/src/lib/assistant.ts` with `POST /assistant/chat` and adapt the response into `ChatMessage` (citations → evidence chips).
4. Map `/api/entities` and `/api/timeline` into the existing `people`/`events` data.
5. Add an optimistic upload row using the returned item, then update it from the status endpoint.
6. Keep mock data as a fallback when the API health check fails so the UI demo remains usable.

## 5. Demo without wiring the UI

The complete workflow is available through Swagger at `/docs`:

1. Upload a screenshot or PDF.
2. Poll status until `completed`.
3. Open `GET /evidence/{id}` for extracted text, entities and timeline events.
4. Open `GET /timeline` and `GET /entities/graph`.
5. Ask the assistant a grounded question.
6. Generate a report and download its PDF.
7. Verify the audit chain at `GET /audit/verify`.
