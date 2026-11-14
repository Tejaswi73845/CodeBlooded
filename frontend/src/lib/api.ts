/**
 * API client for the FastAPI backend.
 * All case data is loaded from the server; nothing is seeded locally.
 */
import type { EvidenceItem } from "@/data/types";

export interface UploadResult {
  id: string;
  hash: string;
}

/** Analyst-supplied capture details recorded when evidence is added. */
export interface UploadMeta {
  date?: string; // YYYY-MM-DD
  time?: string; // HH:MM
  location?: string;
  persons?: string[];
  note?: string;
  /** Let the backend fill blank fields from the file's own content. */
  autoDetect?: boolean;
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
  occurredAt?: string | null;
  location?: string | null;
  persons?: string[];
  captureNote?: string | null;
  captureDetected?: string[];
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
    occurredAt: item.occurredAt ?? undefined,
    location: item.location ?? undefined,
    persons: item.persons ?? [],
    captureNote: item.captureNote ?? undefined,
    captureDetected: item.captureDetected ?? [],
  };
}

/** Base URL for the FastAPI backend. Empty means same-origin (Vite proxies /api in dev). */
const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** True when the id is a backend evidence UUID (seed/local ids are UI-only). */
export const isBackendEvidenceId = (id: string): boolean => UUID_RE.test(id);

let activeWorkspaceId: string | null = null;
let authToken: string | null = null;

/** Select the workspace sent as X-Workspace-Id on every request. */
export function setActiveWorkspace(id: string | null): void {
  activeWorkspaceId = id;
}

/** Set (or clear) the bearer token sent on every request. */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (activeWorkspaceId) headers.set("X-Workspace-Id", activeWorkspaceId);
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

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

export interface BackendEntity {
  id: string;
  type: string;
  value: string;
  normalizedValue: string;
  confidence: number;
  source: string;
  mentionCount: number;
  evidenceCount: number;
  evidenceIds?: string[];
  firstSeenAt?: string;
  lastSeenAt?: string;
}

export interface BackendTimelineEvent {
  id: string;
  at: string | null;
  atRaw?: string | null;
  timeUncertain?: boolean;
  title: string;
  description: string;
  category: string;
  severity: string;
  confidence: number;
  evidenceId: string;
  evidenceIds?: string[];
  evidenceName?: string;
  personIds?: string[];
  location?: string | null;
  extractionSource?: string;
}

export interface BackendAuditEntry {
  id: number;
  actor: string;
  action: string;
  target: string;
  at: string;
  ip?: string | null;
  result: string;
}

export interface BackendReport {
  id: string;
  title: string;
  type: string;
  status: string;
  author: string;
  createdAt: string;
  pages: number;
  evidenceCount: number;
  generatedBy?: string;
}

export interface WorkspaceInfo {
  id: string;
  name: string;
  isDefault: boolean;
  evidenceCount: number;
  createdAt: string;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

export interface AuthResult {
  token: string;
  user: AuthUser;
}

export interface EvidenceAiSummary {
  evidenceId: string;
  evidenceName: string;
  summary: string;
  mode: string;
  model?: string | null;
  cached: boolean;
  generatedAt: string;
  limitations: string[];
}

export const api = {
  async login(email: string, password: string): Promise<AuthResult> {
    const response = await request("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Sign-in failed (HTTP ${response.status})`);
    }
    return (await response.json()) as AuthResult;
  },
  async register(name: string, email: string, password: string): Promise<AuthResult> {
    const response = await request("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Could not create account (HTTP ${response.status})`);
    }
    return (await response.json()) as AuthResult;
  },
  async me(): Promise<AuthUser> {
    const response = await request("/api/auth/me");
    if (!response.ok) throw new Error(`Session expired (HTTP ${response.status})`);
    return (await response.json()) as AuthUser;
  },
  async logout(): Promise<void> {
    await request("/api/auth/logout", { method: "POST" }).catch(() => undefined);
  },
  /** List workspaces with evidence counts. */
  async workspaces(): Promise<WorkspaceInfo[]> {
    const response = await request("/api/workspaces");
    if (!response.ok) throw new Error(`Workspaces request failed (HTTP ${response.status})`);
    return ((await response.json()) as { items?: WorkspaceInfo[] }).items ?? [];
  },
  async createWorkspace(name: string): Promise<WorkspaceInfo> {
    const response = await request("/api/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Could not create workspace (HTTP ${response.status})`);
    }
    return (await response.json()) as WorkspaceInfo;
  },
  async renameWorkspace(id: string, name: string): Promise<WorkspaceInfo> {
    const response = await request(`/api/workspaces/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Could not rename workspace (HTTP ${response.status})`);
    }
    return (await response.json()) as WorkspaceInfo;
  },
  async deleteWorkspace(id: string): Promise<void> {
    const response = await request(`/api/workspaces/${id}`, { method: "DELETE" });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Could not delete workspace (HTTP ${response.status})`);
    }
  },
  async listEvidence(): Promise<EvidenceItem[]> {
    try {
      const response = await request(`/api/evidence?limit=100`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as { items?: BackendEvidence[] };
      return (payload.items ?? []).map(toEvidenceItem);
    } catch {
      // Backend unreachable: show an empty vault rather than fabricated data.
      return [];
    }
  },
  /** Grounded summary of one evidence item. */
  async evidenceSummary(id: string, refresh = false): Promise<EvidenceAiSummary> {
    const response = await request(`/api/evidence/${id}/summary${refresh ? "?refresh=true" : ""}`);
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Summary failed (HTTP ${response.status})`);
    }
    return (await response.json()) as EvidenceAiSummary;
  },
  /** Preserve an uploaded file on the backend with optional capture metadata. */
  async upload(file: File, meta?: UploadMeta): Promise<UploadResult> {
    const form = new FormData();
    form.append("files", file);
    if (meta?.date) form.append("date", meta.date);
    if (meta?.time) form.append("time", meta.time);
    if (meta?.location) form.append("location", meta.location);
    if (meta?.persons?.length) form.append("persons", JSON.stringify(meta.persons));
    if (meta?.note) form.append("note", meta.note);
    if (meta?.autoDetect !== undefined) form.append("autoDetect", meta.autoDetect ? "true" : "false");
    const response = await request(`/api/evidence/upload`, { method: "POST", body: form });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Upload failed (HTTP ${response.status})`);
    }
    const payload = (await response.json()) as { items?: Array<{ id: string; hash: string }> };
    const item = payload.items?.[0];
    if (!item) throw new Error("The server did not preserve this file.");
    return { id: item.id, hash: item.hash };
  },
  /** Fetch one evidence item (to pick up auto-detected capture details). */
  async evidence(id: string): Promise<EvidenceItem> {
    const response = await request(`/api/evidence/${id}`);
    if (!response.ok) throw new Error(`Evidence request failed (HTTP ${response.status})`);
    return toEvidenceItem((await response.json()) as BackendEvidence);
  },
  /** Entities (people, locations, orgs…) extracted from all evidence. */
  async entities(): Promise<BackendEntity[]> {
    const response = await request(`/api/entities?limit=300`);
    if (!response.ok) throw new Error(`Entities request failed (HTTP ${response.status})`);
    return ((await response.json()) as { items?: BackendEntity[] }).items ?? [];
  },
  /** Reconstructed timeline events across all evidence. */
  async timeline(): Promise<BackendTimelineEvent[]> {
    const response = await request(`/api/timeline?limit=500`);
    if (!response.ok) throw new Error(`Timeline request failed (HTTP ${response.status})`);
    return ((await response.json()) as { items?: BackendTimelineEvent[] }).items ?? [];
  },
  /** Correct capture details and re-sync entities/timeline. */
  async updateCapture(id: string, meta: UploadMeta): Promise<EvidenceItem> {
    const response = await request(`/api/evidence/${id}/capture`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date: meta.date ?? null,
        time: meta.time ?? null,
        location: meta.location ?? null,
        persons: meta.persons ?? [],
        note: meta.note ?? null,
      }),
    });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Update failed (HTTP ${response.status})`);
    }
    return toEvidenceItem((await response.json()) as BackendEvidence);
  },
  /** Fetch the extracted text for one evidence item (drawer preview). */
  async evidenceText(id: string): Promise<string[]> {
    const response = await request(`/api/evidence/${id}`);
    if (!response.ok) throw new Error(`Evidence request failed (HTTP ${response.status})`);
    const payload = (await response.json()) as {
      extractedContent?: Array<{ text?: string }>;
    };
    return (payload.extractedContent ?? [])
      .map((content) => content.text ?? "")
      .filter(Boolean)
      .slice(0, 5);
  },
  /** Processing status for a preserved evidence item. */
  async evidenceStatus(id: string): Promise<EvidenceStatusResult> {
    const response = await request(`/api/evidence/${id}/status`);
    if (!response.ok) throw new Error(`Status request failed (HTTP ${response.status})`);
    return (await response.json()) as EvidenceStatusResult;
  },
  /** Download the preserved original file and save it in the browser. */
  async downloadEvidence(id: string, filename: string): Promise<void> {
    const response = await request(`/api/evidence/${id}/download`);
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
    const response = await request(`/api/assistant/chat`, {
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
    const response = await request(`/api/evidence/${id}`, { method: "DELETE" });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Delete failed (HTTP ${response.status})`);
    }
  },
  /** Audit ledger entries. */
  async audit(): Promise<BackendAuditEntry[]> {
    const response = await request(`/api/audit?limit=300`);
    if (!response.ok) throw new Error(`Audit request failed (HTTP ${response.status})`);
    return ((await response.json()) as { items?: BackendAuditEntry[] }).items ?? [];
  },
  /** Saved reports. */
  async reports(): Promise<BackendReport[]> {
    const response = await request(`/api/reports?limit=50`);
    if (!response.ok) throw new Error(`Reports request failed (HTTP ${response.status})`);
    return ((await response.json()) as { items?: BackendReport[] }).items ?? [];
  },
  /** Generate a report on the backend. */
  async generateReport(input: { title?: string; reportType?: string }): Promise<BackendReport> {
    const response = await request(`/api/reports/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: input.title ?? null,
        report_type: input.reportType ?? "incident",
        include_ai_summary: true,
      }),
    });
    if (!response.ok) {
      const payload: { error?: { message?: string } } | null = await response.json().catch(() => null);
      throw new Error(payload?.error?.message ?? `Report generation failed (HTTP ${response.status})`);
    }
    return (await response.json()) as BackendReport;
  },
  /** Download a rendered report PDF. */
  async reportPdf(id: string, filename: string): Promise<void> {
    const response = await request(`/api/reports/${id}/pdf`);
    if (!response.ok) throw new Error(`Report export failed (HTTP ${response.status})`);
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
};
