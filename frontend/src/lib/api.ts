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

/** Base URL for the FastAPI backend. Empty means same-origin (Vite proxies /api in dev). */
const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

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

async function sha256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export const api = {
  async listEvidence(): Promise<EvidenceItem[]> {
    await sleep(120);
    return evidence;
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
  /** Preserve an uploaded file, returning its content hash. */
  async upload(file: File): Promise<UploadResult> {
    return { id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, hash: await sha256(file) };
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
};
