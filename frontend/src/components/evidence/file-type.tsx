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
  image: { label: "Image", tint: "#3f7f86", icon: ImageIcon },
  document: { label: "PDF", tint: "#a2545c", icon: FileText },
  audio: { label: "Audio", tint: "#6f6ba8", icon: Music2 },
  video: { label: "Video", tint: "#9a6a84", icon: Video },
  chat: { label: "Chat", tint: "#4f8a72", icon: MessagesSquare },
  data: { label: "Data", tint: "#a97c34", icon: FileSpreadsheet },
};

export function FileTypeTile({ type, size = "md" }: { type: EvidenceType; size?: "sm" | "md" | "lg" }) {
  const meta = typeMeta[type];
  const Icon = meta.icon;
  const dims =
    size === "sm" ? "h-7 w-7 rounded-[6px]" : size === "lg" ? "h-12 w-12 rounded-[10px]" : "h-9 w-9 rounded-[8px]";
  const iconSize = size === "sm" ? "h-3.5 w-3.5" : size === "lg" ? "h-[22px] w-[22px]" : "h-4 w-4";
  return (
    <span
      className={cn("inline-flex shrink-0 items-center justify-center", dims)}
      style={{
        backgroundColor: `${meta.tint}16`,
        color: meta.tint,
        boxShadow: `inset 0 0 0 1px ${meta.tint}20`,
      }}
    >
      <Icon className={iconSize} strokeWidth={1.7} />
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
