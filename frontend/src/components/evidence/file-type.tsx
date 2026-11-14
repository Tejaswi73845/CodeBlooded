import {
  FileText,
  FileSpreadsheet,
  Image as ImageIcon,
  MessagesSquare,
  Music2,
  Video,
} from "lucide-react";
import type { EvidenceStatus, EvidenceType } from "@/data/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export const typeMeta: Record<
  EvidenceType,
  { label: string; tint: string; icon: typeof FileText }
> = {
  image: { label: "Image", tint: "#007AFF", icon: ImageIcon },
  document: { label: "PDF", tint: "#FF3B30", icon: FileText },
  audio: { label: "Audio", tint: "#5E5CE6", icon: Music2 },
  video: { label: "Video", tint: "#AF52DE", icon: Video },
  chat: { label: "Chat", tint: "#34C759", icon: MessagesSquare },
  data: { label: "Data", tint: "#FF9F0A", icon: FileSpreadsheet },
};

export function FileTypeTile({ type, size = "md" }: { type: EvidenceType; size?: "sm" | "md" | "lg" }) {
  const meta = typeMeta[type];
  const Icon = meta.icon;
  const dims = size === "sm" ? "h-8 w-8 rounded-lg" : size === "lg" ? "h-14 w-14 rounded-2xl" : "h-10 w-10 rounded-[10px]";
  const iconSize = size === "sm" ? "h-3.5 w-3.5" : size === "lg" ? "h-6 w-6" : "h-4 w-4";
  return (
    <span
      className={cn("inline-flex shrink-0 items-center justify-center", dims)}
      style={{ backgroundColor: `${meta.tint}14`, color: meta.tint }}
    >
      <Icon className={iconSize} strokeWidth={1.8} />
    </span>
  );
}

const statusMap: Record<
  EvidenceStatus,
  { label: string; tone: "success" | "accent" | "warning" | "danger" | "neutral"; dot: boolean }
> = {
  processed: { label: "Processed", tone: "success", dot: true },
  processing: { label: "Processing", tone: "accent", dot: true },
  queued: { label: "Queued", tone: "neutral", dot: true },
  review: { label: "Needs review", tone: "warning", dot: true },
  failed: { label: "Failed", tone: "danger", dot: true },
};

export function StatusBadge({ status }: { status: EvidenceStatus }) {
  const meta = statusMap[status];
  return (
    <Badge tone={meta.tone} dot={meta.dot}>
      {meta.label}
    </Badge>
  );
}

export function IntegrityBadge({ integrity }: { integrity: "verified" | "pending" | "mismatch" }) {
  if (integrity === "verified")
    return (
      <span className="inline-flex items-center gap-1 text-[11.5px] font-medium text-success">
        <span className="h-1.5 w-1.5 rounded-full bg-success" /> Verified
      </span>
    );
  if (integrity === "pending")
    return (
      <span className="inline-flex items-center gap-1 text-[11.5px] font-medium text-warning">
        <span className="h-1.5 w-1.5 rounded-full bg-warning" /> Pending
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-[11.5px] font-medium text-danger">
      <span className="h-1.5 w-1.5 rounded-full bg-danger" /> Mismatch
    </span>
  );
}
