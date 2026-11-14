/**
 * API seam for the future FastAPI backend.
 * Replace the mock implementations with `fetch` calls; the store and UI
 * only depend on these signatures.
 */
import { evidence, events, insights, people, pipeline } from "@/data/mock";
import type { EvidenceItem } from "@/data/types";

export interface UploadResult {
  id: string;
  hash: string;
}

export interface EvidenceStatusResult {
  status: string;
  stage: string;
  progress: number;
  error?: string | null;
  integrity: string;
}

interface BackendEvidence {
  id: string;
  reference?: string;
  name: string;
  type: string;
  mime: string;
  size: number;
  uploadedAt: string;
  uploadedBy: string;
  status: string;
  source: string;
  hash: string;
  integrity: string;
  personIds?: string[];
  eventIds?: string[];
  tags?: string[];
  duration?: number;
  pages?: number;
  note?: string | null;
  preview?: string | null;
  error?: string | null;
}

const STATUS_MAP: Record<string, EvidenceItem["status"]> = {
  pending: "queued",
  processing: "processing",
  completed: "processed",
  failed: "failed",
};

function toEvidenceItem(item: BackendEvidence): EvidenceItem {
  const type: EvidenceItem["type"] =
    item.type === "image" ||
    item.type === "document" ||
    item.type === "audio" ||
    item.type === "video" ||
    item.type === "chat" ||
    item.type === "data"
      ? item.type
      : "data";
  return {
    id: item.id,
    name: item.name,
    type,
    mime: item.mime,
    size: item.size,
    uploadedAt: item.uploadedAt,
    uploadedBy: item.uploadedBy,
    status: STATUS_MAP[item.status] ?? "processing",
    source: item.source,
    hash: item.hash,
    tags: item.tags ?? [],
    personIds: item.personIds ?? [],
    eventIds: item.eventIds ?? [],
    note: item.note ?? undefined,
    preview: item.preview ?? undefined,
    integrity: item.integrity === "verified" ? "verified" : item.integrity === "mismatch" ? "mismatch" : "pending",
  };
}

/** Base URL for the FastAPI backend. Empty means same-origin (Vite proxies /api in dev). */
const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** True when the id is a backend evidence UUID (seed/local ids are UI-only). */
export const isBackendEvidenceId = (id: string): boolean => UUID_RE.test(id);

export interface ChatSource {
  evidenceId: string;
  evidenceName: string;
  fileType: string;
  excerpt: string;
  pageNumber?: number | null;
  timestampStart?: number | null;
  timestampEnd?: number | null;
  relevance: number;
  locator?: string | null;
}

export interface ChatResult {
  answer: string;
  insufficientEvidence: boolean;
  sources: ChatSource[];
  mode: string;
  model?: string | null;
  limitations: string[];
  retrievalMode: string;
  chunksConsidered: number;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const api = {
  async listEvidence(): Promise<EvidenceItem[]> {
    try {
      const response = await fetch(`${API_BASE}/api/evidence?limit=100`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as { items?: BackendEvidence[] };
      return (payload.items ?? []).map(toEvidenceItem);
    } catch {
      // Backend unreachable: keep the seeded demo vault.
      return evidence;
    }
  },
  async listPeople() {
    await sleep(80);
    return people;
  },
  async listEvents() {
    await sleep(80);
    return events;
  },
  async listInsights() {
    await sleep(80);
    return insights;
  },
  async pipeline() {
    await sleep(60);
    return pipeline;
  },
  /** Preserve an uploaded file on the backend, returning its id and content hash. */
  async upload(file: File): Promise<UploadResult> {
    const form = new FormData();
    form.append("files", file);
    const response = await fetch(`${API_BASE}/api/evidence/upload`, { method: "POST", body: form });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Upload failed (HTTP ${response.status})`);
    }
    const payload = (await response.json()) as { items?: Array<{ id: string; hash: string }> };
    const item = payload.items?.[0];
    if (!item) throw new Error("The server did not preserve this file.");
    return { id: item.id, hash: item.hash };
  },
  /** Processing status for a preserved evidence item. */
  async evidenceStatus(id: string): Promise<EvidenceStatusResult> {
    const response = await fetch(`${API_BASE}/api/evidence/${id}/status`);
    if (!response.ok) throw new Error(`Status request failed (HTTP ${response.status})`);
    return (await response.json()) as EvidenceStatusResult;
  },
  /** Download the preserved original file and save it in the browser. */
  async downloadEvidence(id: string, filename: string): Promise<void> {
    const response = await fetch(`${API_BASE}/api/evidence/${id}/download`);
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Download failed (HTTP ${response.status})`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  },
  /** Ask the evidence-grounded assistant (FastAPI POST /api/assistant/chat). */
  async chat(question: string, evidenceIds: string[] = [], limit = 8): Promise<ChatResult> {
    const response = await fetch(`${API_BASE}/api/assistant/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, evidence_ids: evidenceIds, limit }),
    });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Assistant request failed (HTTP ${response.status})`);
    }
    return (await response.json()) as ChatResult;
  },
  /** Remove an evidence item from the active vault (soft delete; original retained). */
  async deleteEvidence(id: string): Promise<void> {
    // Seed items and local intakes exist only in the UI, not on the backend.
    if (!UUID_RE.test(id)) return;
    const response = await fetch(`${API_BASE}/api/evidence/${id}`, { method: "DELETE" });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Delete failed (HTTP ${response.status})`);
    }
  },
};
