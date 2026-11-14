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
};
