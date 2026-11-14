import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "soft";
type Size = "sm" | "md" | "icon" | "lg";

const variants: Record<Variant, string> = {
  primary:
    "bg-accent text-white shadow-[0_1px_2px_rgba(0,0,0,0.12)] hover:brightness-110 active:brightness-95",
  secondary:
    "bg-surface text-ink border border-line hover:bg-surface-2 active:bg-surface-3",
  ghost: "text-ink-2 hover:text-ink hover:bg-surface-3/70",
  danger: "bg-danger text-white hover:brightness-110",
  soft: "bg-accent-soft text-accent hover:brightness-[0.97] dark:hover:brightness-110",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-[13px] gap-1.5 rounded-lg",
  md: "h-9 px-3.5 text-[13px] gap-2 rounded-[10px]",
  lg: "h-11 px-5 text-sm gap-2 rounded-xl",
  icon: "h-8 w-8 rounded-lg justify-center",
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
        "inline-flex items-center justify-center whitespace-nowrap font-medium transition-[background,color,filter,transform] duration-150 disabled:pointer-events-none disabled:opacity-45",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}
