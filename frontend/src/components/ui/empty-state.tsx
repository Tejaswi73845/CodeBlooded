import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-16 text-center", className)}>
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-[10px] border border-line bg-surface-2 text-ink-3">
        <Icon className="h-[18px] w-[18px]" strokeWidth={1.7} />
      </div>
      <p className="font-serif text-[17px] font-medium leading-tight">{title}</p>
      <p className="mt-1.5 max-w-xs text-[12.5px] leading-relaxed text-ink-2">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
