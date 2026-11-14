import { Search } from "lucide-react";
import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-9 w-full rounded-[8px] border border-line-strong/70 bg-surface px-3 text-[13px] text-ink shadow-[inset_0_1px_0_rgba(25,28,24,0.02)] placeholder:text-ink-3 transition-[border-color,box-shadow] focus:border-accent/70 focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--accent)_12%,transparent)] focus:outline-none",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export function SearchInput({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className={cn("relative", className)}>
      <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-3" />
      <Input className="pl-8 pr-8" {...props} />
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[12px] font-medium tracking-[-0.005em] text-ink-2">{label}</span>
      {children}
      {hint && <span className="text-[11px] leading-relaxed text-ink-3">{hint}</span>}
    </label>
  );
}
