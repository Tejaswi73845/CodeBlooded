import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function StatStrip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "grid grid-cols-2 divide-y divide-line overflow-hidden rounded-card border border-line bg-surface shadow-card sm:grid-cols-4 sm:divide-x sm:divide-y-0",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  footnote,
  icon: Icon,
  tint = "#7a2e36",
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
    <div className="relative px-4 py-3.5">
      <span className="absolute left-4 top-0 h-[2px] w-9 opacity-70" style={{ backgroundColor: tint }} aria-hidden />
      <div className="flex items-start justify-between gap-3">
        <span className="docket-label leading-tight">{label}</span>
        <Icon className="mt-px h-3.5 w-3.5 shrink-0" style={{ color: tint }} strokeWidth={1.9} />
      </div>
      <div className="mt-2.5 flex items-baseline gap-2">
        <span className="font-serif text-[36px] font-normal leading-none tracking-[-0.035em] tabular-nums">
          {value}
        </span>
        {trend && (
          <span
            className={cn(
              "rounded-[4px] px-1 py-0.5 font-mono text-[9.5px] font-medium tabular-nums",
              trend.startsWith("+") ? "bg-success/10 text-success" : "bg-surface-3 text-ink-3",
            )}
          >
            {trend}
          </span>
        )}
      </div>
      <p className="mt-3 truncate border-t border-line pt-2 text-[10.5px] leading-snug text-ink-3">
        {footnote}
      </p>
    </div>
  );
}
