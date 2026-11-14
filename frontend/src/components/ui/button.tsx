import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "soft";
type Size = "sm" | "md" | "icon" | "lg";

const variants: Record<Variant, string> = {
  primary:
    "bg-accent text-on-accent shadow-[inset_0_1px_0_rgba(255,255,255,0.14),0_1px_2px_rgba(50,20,20,0.28)] hover:bg-accent-strong",
  secondary:
    "border border-line-strong/70 bg-surface text-ink shadow-[0_1px_1px_rgba(25,28,24,0.03)] hover:border-line-strong hover:bg-surface-2",
  ghost: "text-ink-2 hover:bg-surface-3/70 hover:text-ink",
  danger:
    "bg-danger text-on-accent shadow-[inset_0_1px_0_rgba(255,255,255,0.12),0_1px_2px_rgba(50,20,20,0.22)] hover:brightness-95",
  soft: "bg-accent-soft text-accent hover:bg-accent-soft/75",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-[12.5px] gap-1.5 rounded-[8px]",
  md: "h-9 px-3.5 text-[13px] gap-2 rounded-[9px]",
  lg: "h-11 px-5 text-[13.5px] gap-2 rounded-[10px]",
  icon: "h-9 w-9 rounded-[9px] justify-center",
};

export function Button({
  className,
  variant = "secondary",
  size = "md",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap font-medium tracking-[-0.006em] transition-[background-color,border-color,color,box-shadow,transform] duration-150 active:translate-y-px disabled:pointer-events-none disabled:opacity-45",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}
