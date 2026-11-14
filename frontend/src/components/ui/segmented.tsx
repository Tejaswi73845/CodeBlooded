import { cn } from "@/lib/utils";

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  className,
  size = "md",
}: {
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: string }[];
  className?: string;
  size?: "sm" | "md";
}) {
  return (
    <div
      role="tablist"
      className={cn(
        "inline-flex items-center gap-[3px] rounded-[8px] border border-line bg-surface-2 p-[3px]",
        className,
      )}
    >
      {options.map((option) => (
        <button
          key={option.value}
          role="tab"
          aria-selected={value === option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            "rounded-[6px] font-medium transition-all duration-150",
            size === "sm" ? "h-6 px-2.5 text-[11.5px]" : "h-7 px-3 text-[12px]",
            value === option.value
              ? "border border-line bg-surface text-ink shadow-[0_1px_2px_rgba(25,28,24,0.06)]"
              : "border border-transparent text-ink-2 hover:text-ink",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-[24px] w-[42px] shrink-0 rounded-full border transition-colors duration-200",
        checked ? "border-success/40 bg-success" : "border-line-strong bg-line-strong/70",
      )}
    >
      <span
        className={cn(
          "absolute left-0 top-[2px] h-[18px] w-[18px] rounded-full bg-white shadow-[0_1px_3px_rgba(25,28,24,0.3)] transition-transform duration-200",
          checked ? "translate-x-[21px]" : "translate-x-[2px]",
        )}
      />
    </button>
  );
}
