# Veritas — TraceVault Frontend

React 19 + TypeScript interface for TraceVault. It is fully wired to the FastAPI backend: there is **no demo dataset** — evidence, people, timeline events, reports and audit entries all come from the API.

Screens: Dashboard · Evidence Vault · Timeline · People & Connections · AI Assistant · Reports · Audit · Settings.

**Workspaces:** the sidebar switcher lists only **your** workspaces and lets you create, rename or delete them. Every screen is scoped to the selected workspace (the client sends `X-Workspace-Id`); the backend rejects workspaces owned by other accounts. Switching reloads evidence, people, timeline, reports, audit and chat. Deleting a workspace moves its data to your default workspace. Each new account gets its own default workspace at sign-up.

## Prerequisites

Start the backend first (see [`../backend/README.md`](../backend/README.md)):

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

## Run

```bash
npm install
npm run dev
```

Open <http://localhost:5173>. Light theme is default; toggle dark from the topbar.

**Sign in** with the seeded account (`aarav.shah@kestrel.legal` / `tracevault`) or create a new one on the same screen. The session token is stored in `localStorage` and sent as `Authorization: Bearer …`; **Sign out** in the account menu revokes it server-side.

### Backend connection

In development, `vite.config.ts` proxies `/api` to `http://localhost:8000`, so no client configuration is required:

```ts
server: {
  proxy: {
    "/api": { target: process.env.VITE_BACKEND_URL ?? "http://localhost:8000", changeOrigin: true },
  },
}
```

- Override the dev target: `VITE_BACKEND_URL=http://host:8000 npm run dev`
- Build for another origin: set `VITE_API_URL=http://host:8000` in `frontend/.env.local`, then `npm run build` (baked at build time)
- **Restart the dev server** after touching the proxy config.

### Production build

```bash
npm run build     # tsc -b && vite build
npm run preview   # serves dist/
```

Serve `dist/` behind the same origin as the API, or set `VITE_API_URL` / reverse-proxy `/api`.

## Stack

React 19 · TypeScript · Vite · Tailwind CSS v4 · Radix primitives · Lucide · React Flow (connection graph) · Recharts (dashboard chart). Components follow the shadcn-style structure in `src/components/ui`.

## Design system

The interface is art-directed as a working case file: stone-paper surfaces, ink text, an oxblood action colour and verdigris for verified states. **Newsreader** (serif) carries page titles, card headings and the report; **IBM Plex Sans** runs the interface; **IBM Plex Mono** is reserved for hashes, timestamps, case references and ledger data. Tokens, type scale, motion and both light/dark themes live in `src/index.css`; fonts are bundled locally via `@fontsource` (latin subsets) so the app does not depend on a font CDN.

## Structure

```
src/
  components/
    layout/        sidebar, topbar, command palette
    evidence/      drawer, preview, upload/edit capture dialog, file tiles
    ui/            button, dialog, sheet, input, badge, progress, toast…
  pages/           dashboard, vault, timeline, people, assistant, reports, audit, settings
  store/           app store: evidence/people/events/audit loading, uploads, chat, toasts, theme
  lib/
    api.ts         typed API client (all backend calls)
    assistant.ts   chat helper + suggested prompts
    workspace.ts   workspace labels (case name/analyst)
    format.ts      date/size/hash formatting
  data/types.ts    shared UI types
  index.css        design tokens and global styles
```

## What the UI does

### Evidence Vault

- Drag-and-drop or browse to upload. A **capture details** dialog collects date, time, location, people and a note — all optional.
- **Auto-detect missing details from the file** (default on): the backend fills blanks after processing; detected fields are labelled in the drawer.
- List/grid views, search, type/status/person filters, sorting, per-file progress driven by real `GET /evidence/{id}/status` polling.
- **Verify vault** re-hashes every original in the workspace, updates integrity badges and verifies the audit ledger, then reports counts. The drawer also has a per-item **Verify integrity** action.
- Completed items missing capture details (date, location or people) are shown as **Needs review**; use the check action (list, grid or drawer) to **mark reviewed / skip**, or add the details first.
- Processed items carry a context-based **Critical / Attention / Normal** priority tag, aligned with timeline severity:
  - **Critical** — threat, bullying, coercion, fraud or an integrity mismatch
  - **Attention** — rude/angry/hostile language or a warning event
  - **Normal** — no risk signal detected
  Review and failed states are communicated by their status badge instead of a duplicate priority tag.
- The drawer shows an **AI evidence summary** with a regenerate action.
- Drawer: real extracted text, capture metadata, integrity hash, linked people/events.
  - **Edit details** corrects date/location/people/note (`PATCH /evidence/{id}/capture`).
  - **Download** fetches the preserved original (`GET /evidence/{id}/download`).
  - **Remove** soft-deletes the item (original retained; audited).

### Dashboard

Real counts, a 7-day intake chart computed from upload dates, processing pipeline derived from evidence statuses, recent evidence/events, and a **summary of the newest uploaded evidence** (AI-generated, with an extractive fallback) with Open/Refresh actions.

### Timeline

Events from `GET /timeline` (including capture events), grouped by day. Each card shows an **AI summary**, a shared **Critical / Attention / Normal** severity tag (same classification as the evidence vault), date/day, raw and normalised time, location, linked people and source files, plus an **Edit** action to correct date/time/location and to **re-summarise with investigator context**. Summaries are generated on demand via `POST /timeline/summaries` and cached.

### People & Connections

Nodes from `GET /entities?type=person`; edges connect people who appear in the same evidence item. Nodes are clickable and link back to their evidence.

### AI Assistant

Grounded Q&A via `POST /assistant/chat` with source chips for citations. A **Sources used** panel shows exactly which evidence passages the last answer pulled from (file, excerpt, locator, relevance) and appears only after a question has been answered. Answers degrade to labelled extractive mode when the AI provider is unavailable or out of balance; configuration is server-side.

### Reports

A single live document preview built from your evidence, people and timeline. A **Disclosure check** at the top lists readiness items (evidence preserved, integrity verified, required sections enabled, case type identified, people resolved). The **Incident summary** shows AI case-type tags (e.g. Fraud, Harassment, Assault, Sexual assault, Threats & extortion, Cybercrime) with confidence and a detailed AI summary. A dedicated **Out-of-scope / unrelated evidence** section lists items that do not belong to the case with the reason. **Document settings** opens a popup with section switches; changes update the preview live and the preview always uses the full page width. **Download PDF** prints the live preview (choose *Save as PDF*), so only the enabled sections are included.

### Audit

Append-only ledger from `GET /audit` with search/filter and CSV export.

## Data flow

All requests go through `src/lib/api.ts`:

| Area | Endpoint(s) |
|---|---|
| Evidence list/detail/status | `GET /evidence`, `/evidence/{id}`, `/evidence/{id}/status` |
| Upload (with capture metadata) | `POST /evidence/upload` (multipart) |
| Edit capture details | `PATCH /evidence/{id}/capture` |
| Download / delete | `GET /evidence/{id}/download`, `DELETE /evidence/{id}` |
| People / graph | `GET /entities` |
| Timeline | `GET /timeline` |
| Assistant | `POST /assistant/chat` |
| Reports | `GET /reports`, `POST /reports/generate`, `GET /reports/{id}/pdf` |
| Audit | `GET /audit` |

API responses are camelCase with UTC (`Z`) timestamps. Errors use `{ error: { code, message, details, requestId } }`; the UI surfaces `message` in toasts.

## Notes

- No mock fallback: if the backend is unreachable, lists are empty and uploads/downloads show an error toast.
- Images uploaded in-session preview from a browser object URL; other files show their extracted text.
- PDF export uses the server-rendered report when available and falls back to browser print.
- Upload/edit dialogs are scrollable (`max-h-[85dvh]`).

## Checks

```bash
npm run build      # TypeScript project build + production bundle
```
