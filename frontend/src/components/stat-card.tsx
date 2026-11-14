import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  footnote,
  icon: Icon,
  tint = "#007AFF",
  trend,
}: {
  label: string;
  value: string | number;
  footnote: string;
  icon: LucideIcon;
  tint?: string;
  trend?: string;
}) {
  return (
    <div className="rounded-card border border-line bg-surface p-4 shadow-card transition-shadow duration-200 hover:shadow-[0_2px_4px_rgba(0,0,0,0.04),0_8px_24px_rgba(0,0,0,0.05)]">
      <div className="flex items-start justify-between gap-2">
        <span className="text-[12.5px] font-medium text-ink-2">{label}</span>
        <span
          className="flex h-7 w-7 items-center justify-center rounded-[8px]"
          style={{ backgroundColor: `${tint}14`, color: tint }}
        >
          <Icon className="h-3.5 w-3.5" strokeWidth={2} />
        </span>
      </div>
      <div className="mt-2.5 flex items-baseline gap-2">
        <span className="text-[27px] font-semibold leading-none tracking-[-0.03em] tabular-nums">{value}</span>
        {trend && (
          <span className={cn("text-[11px] font-medium", trend.startsWith("+") ? "text-success" : "text-ink-3")}>
            {trend}
          </span>
        )}
      </div>
      <p className="mt-2 text-[11.5px] text-ink-3">{footnote}</p>
    </div>
  );
}
