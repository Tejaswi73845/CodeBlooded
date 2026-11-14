# Veritas — TraceVault Frontend

A production-style React interface for TraceVault, an AI-powered digital evidence platform. Organise preserved evidence, reconstruct an incident timeline, inspect entity relationships, ask grounded questions and assemble a court-ready report.

Runs standalone with typed demo data; the FastAPI contract that replaces the demo store is documented in [`../docs/FRONTEND_INTEGRATION.md`](../docs/FRONTEND_INTEGRATION.md).

## Run

```bash
npm install
npm run dev
npm run build
```

Open `http://localhost:5173`. Light appearance is the default; use the topbar toggle for dark.

## Stack

React 19 · TypeScript · Vite · Tailwind CSS v4 · Radix primitives · Lucide · React Flow · Recharts. No UI-kit template: components live in `src/components/ui` in the shadcn style.

## Structure

```
src/
  components/       layout, evidence, UI primitives
  pages/            eight routes, state-driven
  store/            app store: evidence, uploads, chat, theme, toasts
  data/             typed realistic demo data
  lib/              api seam, assistant mock, formatting
  index.css         design tokens and global styles
public/             favicon and static assets
```

## Backend seam

`src/lib/api.ts` is the integration point. Replace the mock implementations (`listEvidence`, `upload`, …) with calls to the TraceVault backend; the store and pages only depend on those signatures. Uploads already compute a real SHA-256 digest with Web Crypto before the item enters the vault.

## Demo behaviour

Search (`⌘K`), filters, drag-and-drop upload, evidence preview drawer, graph inspection, timeline filtering, assistant Q&A with citations, report generation and PDF export (via print), audit CSV export, notifications and theme switching all work against local mock state.
