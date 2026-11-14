import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "accent" | "success" | "warning" | "danger" | "violet";

const tones: Record<Tone, string> = {
  neutral: "border-line bg-surface-3/60 text-ink-2",
  accent: "border-accent/20 bg-accent-soft text-accent",
  success: "border-success/20 bg-success/10 text-success",
  warning: "border-warning/25 bg-warning/12 text-warning",
  danger: "border-danger/20 bg-danger/10 text-danger",
  violet: "border-violet/20 bg-violet/10 text-violet",
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
        "inline-flex h-[21px] items-center gap-1.5 whitespace-nowrap rounded-[5px] border px-1.5 text-[10.5px] font-medium leading-none tracking-[0.005em]",
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
