import { Badge } from "@/components/ui/badge";
import type { EvidenceItem, IncidentEvent } from "@/data/types";

export type EvidencePriority = "critical" | "attention" | "normal";

/** Derive a review priority for an evidence item from its integrity and linked events. */
export function evidencePriority(item: EvidenceItem, events: IncidentEvent[]): EvidencePriority {
  const linked = events.filter(
    (event) => event.evidenceIds.includes(item.id) || (item.eventIds ?? []).includes(event.id),
  );
  const linkedCritical = linked.some((event) => event.severity === "critical");
  const linkedWarning = linked.some((event) => event.severity === "warning");
  if (item.integrity === "mismatch" || linkedCritical) return "critical";
  if (
    linkedWarning ||
    item.needsReview ||
    item.status === "review" ||
    item.status === "failed" ||
    (item.status === "processed" && item.integrity === "pending")
  ) {
    return "attention";
  }
  return "normal";
}

const META: Record<EvidencePriority, { label: string; tone: "danger" | "warning" | "success" }> = {
  critical: { label: "Critical", tone: "danger" },
  attention: { label: "Attention", tone: "warning" },
  normal: { label: "Normal", tone: "success" },
};

export function eventSeverityTag(severity: string): EvidencePriority {
  if (severity === "critical") return "critical";
  if (severity === "warning") return "attention";
  return "normal";
}

export function SeverityBadge({
  tag,
  className,
}: {
  tag: EvidencePriority;
  className?: string;
}) {
  const meta = META[tag];
  return (
    <Badge tone={meta.tone} dot className={className ?? "h-[18px] text-[9.5px]"}>
      {meta.label}
    </Badge>
  );
}

export function PriorityBadge({ priority }: { priority: EvidencePriority }) {
  return <SeverityBadge tag={priority} />;
}
