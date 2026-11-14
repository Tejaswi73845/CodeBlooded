import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "accent" | "success" | "warning" | "danger" | "violet";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-3 text-ink-2",
  accent: "bg-accent-soft text-accent",
  success: "bg-success/12 text-[#248a3d] dark:text-success",
  warning: "bg-warning/14 text-[#b25f00] dark:text-warning",
  danger: "bg-danger/12 text-[#d70015] dark:text-danger",
  violet: "bg-violet/12 text-[#4b49c8] dark:text-violet",
};

const dots: Record<Tone, string> = {
  neutral: "bg-ink-3",
  accent: "bg-accent",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  violet: "bg-violet",
};

export function Badge({
  tone = "neutral",
  dot,
  className,
  children,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone; dot?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center gap-1.5 rounded-md px-2 text-[11.5px] font-medium leading-none",
        tones[tone],
        className,
      )}
      {...props}
    >
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full", dots[tone])} />}
      {children}
    </span>
  );
}
