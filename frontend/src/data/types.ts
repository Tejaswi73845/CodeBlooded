export type EvidenceType = "image" | "document" | "audio" | "video" | "chat" | "data";
export type EvidenceStatus = "processed" | "processing" | "queued" | "review" | "failed";
export type Severity = "info" | "warning" | "critical";
export type RiskLevel = "low" | "medium" | "high";

export interface Person {
  id: string;
  name: string;
  role: string;
  initials: string;
  tint: string;
  risk: RiskLevel;
  phone?: string;
  email?: string;
  location?: string;
  evidenceCount: number;
  lastSeen: string;
  note: string;
}

export interface EvidenceItem {
  id: string;
  name: string;
  type: EvidenceType;
  mime: string;
  size: number;
  uploadedAt: string;
  uploadedBy: string;
  status: EvidenceStatus;
  source: string;
  hash: string;
  tags: string[];
  personIds: string[];
  eventIds: string[];
  duration?: number;
  pages?: number;
  note?: string;
  preview?: string;
  url?: string;
  integrity: "verified" | "pending" | "mismatch";
}

export type EventCategory = "Communication" | "Financial" | "Physical" | "Digital" | "Legal";

export interface IncidentEvent {
  id: string;
  at: string;
  title: string;
  description: string;
  category: EventCategory;
  severity: Severity;
  personIds: string[];
  evidenceIds: string[];
  location?: string;
}

export type InsightKind = "link" | "anomaly" | "pattern" | "summary";

export interface Insight {
  id: string;
  kind: InsightKind;
  title: string;
  body: string;
  confidence: number;
  severity: Severity;
  evidenceIds: string[];
  createdAt: string;
  reviewed: boolean;
}

export interface AuditEntry {
  id: string;
  actor: string;
  action: string;
  target: string;
  at: string;
  ip: string;
  result: "success" | "warning" | "denied";
}

export interface AppNotification {
  id: string;
  title: string;
  body: string;
  at: string;
  read: boolean;
  kind: "insight" | "processing" | "integrity" | "system";
}

export interface PipelineStage {
  label: string;
  detail: string;
  progress: number;
  state: "done" | "active" | "queued";
}

export interface ReportRecord {
  id: string;
  title: string;
  type: string;
  status: "Draft" | "Final" | "Review";
  createdAt: string;
  pages: number;
  author: string;
  evidenceCount: number;
}

export interface GraphNode {
  id: string;
  kind: "person" | "phone" | "email" | "conversation" | "event";
  label: string;
  sublabel?: string;
  personId?: string;
}
