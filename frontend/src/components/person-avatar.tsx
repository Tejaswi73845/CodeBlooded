import type { Person } from "@/data/types";
import { cn } from "@/lib/utils";
import { initials } from "@/lib/format";

const sizes = {
  xs: "h-6 w-6 text-[9.5px]",
  sm: "h-7 w-7 text-[10px]",
  md: "h-9 w-9 text-[11px]",
  lg: "h-11 w-11 text-[12px]",
  xl: "h-14 w-14 text-[15px]",
};

export function PersonAvatar({
  person,
  size = "md",
  className,
  ring,
}: {
  person: Pick<Person, "name" | "tint">;
  size?: keyof typeof sizes;
  className?: string;
  ring?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold tracking-[0.01em]",
        sizes[size],
        ring && "ring-2 ring-surface",
        className,
      )}
      style={{ backgroundColor: `${person.tint}22`, color: person.tint }}
      aria-hidden
    >
      {initials(person.name)}
    </span>
  );
}

export function AvatarStack({ people, max = 4 }: { people: Pick<Person, "name" | "tint">[]; max?: number }) {
  const shown = people.slice(0, max);
  const extra = people.length - shown.length;
  return (
    <span className="flex items-center -space-x-1.5">
      {shown.map((p) => (
        <PersonAvatar key={p.name} person={p} size="xs" ring />
      ))}
      {extra > 0 && (
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-surface-3 text-[9.5px] font-medium text-ink-2 ring-2 ring-surface">
          +{extra}
        </span>
      )}
    </span>
  );
}
