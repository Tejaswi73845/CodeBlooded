import {
  Banknote,
  CalendarClock,
  Download,
  FileText,
  Gavel,
  MapPin,
  MessageSquare,
  MonitorSmartphone,
  RotateCcw,
  ShieldAlert,
  Waypoints,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useApp } from "@/store/app-store";
import type { EventCategory } from "@/data/types";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PersonAvatar } from "@/components/person-avatar";
import { FileTypeTile } from "@/components/evidence/file-type";
import { formatDate, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const categories: { value: "all" | EventCategory; label: string }[] = [
  { value: "all", label: "All events" },
  { value: "Communication", label: "Communication" },
  { value: "Financial", label: "Financial" },
  { value: "Physical", label: "Physical" },
  { value: "Digital", label: "Digital" },
  { value: "Legal", label: "Legal" },
];

const categoryMeta: Record<EventCategory, { icon: typeof MessageSquare; tint: string }> = {
  Communication: { icon: MessageSquare, tint: "#007AFF" },
  Financial: { icon: Banknote, tint: "#34C759" },
  Physical: { icon: Waypoints, tint: "#FF9F0A" },
  Digital: { icon: MonitorSmartphone, tint: "#5E5CE6" },
  Legal: { icon: Gavel, tint: "#86868B" },
};

const longDate = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
});

export function TimelinePage() {
  const { events, people, evidence, openEvidence, navigate, toast } = useApp();
  const [category, setCategory] = useState<"all" | EventCategory>("all");
  const [person, setPerson] = useState("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const filtered = useMemo(() => {
    return [...events]
      .filter((e) => {
        if (category !== "all" && e.category !== category) return false;
        if (person !== "all" && !e.personIds.includes(person)) return false;
        const day = e.at.slice(0, 10);
        if (from && day < from) return false;
        if (to && day > to) return false;
        return true;
      })
      .sort((a, b) => +new Date(a.at) - +new Date(b.at));
  }, [events, category, person, from, to]);

  const groups = useMemo(() => {
    const map = new Map<string, typeof filtered>();
    filtered.forEach((event) => {
      const key = event.at.slice(0, 10);
      map.set(key, [...(map.get(key) ?? []), event]);
    });
    return [...map.entries()];
  }, [filtered]);

  const hasFilters = category !== "all" || person !== "all" || from !== "" || to !== "";

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={
          <>
            <Badge tone="accent" dot>
              Reconstructed from {evidence.length} sources
            </Badge>
            <span className="text-[11px] text-ink-3">
              {events.length > 0
                ? `${formatDate(new Date(Math.min(...events.map((event) => +new Date(event.at)))).toISOString())} – ${formatDate(
                    new Date(Math.max(...events.map((event) => +new Date(event.at)))).toISOString(),
                  )}`
                : "No dated events yet"}
            </span>
          </>
        }
        title="Incident Timeline"
        description="Every event is anchored to a preserved source. Select an event to open the evidence it rests on."
        actions={
          <>
            <Button
              variant="secondary"
              onClick={() => toast("Timeline exported", "Chronology PDF prepared with evidence references.", "success")}
            >
              <Download className="h-3.5 w-3.5" /> Export
            </Button>
            <Button variant="primary" onClick={() => navigate("reports")}>
              <FileText className="h-3.5 w-3.5" /> Build report
            </Button>
          </>
        }
      />

      <div className="mb-4 rounded-card border border-line bg-surface p-3 shadow-card">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap items-center gap-1">
            {categories.map((c) => (
              <button
                key={c.value}
                onClick={() => setCategory(c.value)}
                aria-pressed={category === c.value}
                className={cn(
                  "h-7 rounded-full px-2.5 text-[11.5px] font-medium transition-colors",
                  category === c.value
                    ? "bg-ink text-surface"
                    : "bg-surface-2 text-ink-2 hover:bg-surface-3 hover:text-ink",
                )}
              >
                {c.label}
              </button>
            ))}
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-1.5">
            <label className="flex items-center gap-1.5 text-[11px] text-ink-3">
              Person
              <select
                value={person}
                onChange={(e) => setPerson(e.target.value)}
                aria-label="Filter by person"
                className="h-8 max-w-[160px] rounded-lg border border-line bg-surface px-2 text-[11.5px] text-ink outline-none"
              >
                <option value="all">Anyone</option>
                {people.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5 text-[11px] text-ink-3">
              From
              <input
                type="date"
                value={from}
                min="2026-11-01"
                max="2026-11-30"
                onChange={(e) => setFrom(e.target.value)}
                aria-label="Filter from date"
                className="h-8 rounded-lg border border-line bg-surface px-2 text-[11.5px] text-ink outline-none"
              />
            </label>
            <label className="flex items-center gap-1.5 text-[11px] text-ink-3">
              To
              <input
                type="date"
                value={to}
                min="2026-11-01"
                max="2026-11-30"
                onChange={(e) => setTo(e.target.value)}
                aria-label="Filter to date"
                className="h-8 rounded-lg border border-line bg-surface px-2 text-[11.5px] text-ink outline-none"
              />
            </label>
            {hasFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setCategory("all");
                  setPerson("all");
                  setFrom("");
                  setTo("");
                }}
              >
                <RotateCcw className="h-3 w-3" /> Reset
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between px-1 pb-3 text-[11px] text-ink-3">
        <span>
          {filtered.length} event{filtered.length === 1 ? "" : "s"} in view
          {person !== "all" && people.find((p) => p.id === person) ? ` · ${people.find((p) => p.id === person)!.name}` : ""}
        </span>
        <span className="inline-flex items-center gap-3">
          <span className="inline-flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-danger" /> Critical
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-warning" /> Attention
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" /> Recorded
          </span>
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-card border border-line bg-surface shadow-card">
          <EmptyState
            icon={CalendarClock}
            title="No events in this window"
            description="Adjust the date range or clear the person filter to see the full chronology."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setCategory("all");
                  setPerson("all");
                  setFrom("");
                  setTo("");
                }}
              >
                Reset filters
              </Button>
            }
          />
        </div>
      ) : (
        <div className="space-y-6">
          {groups.map(([day, dayEvents]) => (
            <section key={day} aria-label={longDate.format(new Date(`${day}T12:00:00`))}>
              <div className="sticky top-14 z-10 -mx-1 mb-2 flex items-center gap-2 rounded-lg bg-bg/90 px-1 py-1.5 backdrop-blur-md">
                <h2 className="text-[12.5px] font-semibold">{longDate.format(new Date(`${day}T12:00:00`))}</h2>
                <span className="text-[11px] text-ink-3">
                  {dayEvents.length} event{dayEvents.length === 1 ? "" : "s"}
                </span>
                {dayEvents.some((e) => e.severity === "critical") && (
                  <Badge tone="danger" className="ml-1 h-[18px] text-[10px]">
                    <ShieldAlert className="mr-0.5 h-2.5 w-2.5" /> critical window
                  </Badge>
                )}
              </div>

              <div className="relative">
                <div className="absolute bottom-2 left-[76px] top-2 w-px bg-line sm:left-[92px]" aria-hidden />
                <ol className="space-y-2.5">
                  {dayEvents.map((event) => {
                    const meta = categoryMeta[event.category];
                    const linkedPeople = people.filter((p) => event.personIds.includes(p.id));
                    const sources = evidence.filter((e) => event.evidenceIds.includes(e.id));
                    return (
                      <li key={event.id} className="relative grid grid-cols-[56px_1fr] gap-3 sm:grid-cols-[70px_1fr] sm:gap-4">
                        <div className="pt-3 text-right">
                          <span className="block text-[12px] font-semibold tabular-nums tracking-tight">
                            {formatTime(event.at)}
                          </span>
                          <span className="mt-0.5 block text-[9.5px] uppercase tracking-wide text-ink-3">
                            IST
                          </span>
                        </div>
                        <span
                          className={cn(
                            "absolute left-[72px] top-[19px] z-[1] h-2.5 w-2.5 -translate-x-1/2 rounded-full border-2 border-surface sm:left-[88px]",
                            event.severity === "critical"
                              ? "bg-danger"
                              : event.severity === "warning"
                                ? "bg-warning"
                                : "bg-accent",
                          )}
                          aria-hidden
                        />
                        <div
                          onClick={() => event.evidenceIds[0] && openEvidence(event.evidenceIds[0])}
                          className={cn(
                            "cursor-pointer rounded-xl border border-line bg-surface p-3.5 shadow-card transition-all duration-200 hover:border-line-strong hover:shadow-[0_2px_4px_rgba(0,0,0,0.04),0_8px_24px_rgba(0,0,0,0.05)]",
                            event.severity === "critical" && "border-l-[3px] border-l-danger",
                          )}
                        >
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                            <span
                              className="flex h-5 w-5 items-center justify-center rounded-md"
                              style={{ backgroundColor: `${meta.tint}14`, color: meta.tint }}
                            >
                              <meta.icon className="h-3 w-3" />
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                event.evidenceIds[0] && openEvidence(event.evidenceIds[0]);
                              }}
                              className="text-left text-[13px] font-medium hover:text-accent"
                            >
                              {event.title}
                            </button>
                            <Badge tone="neutral" className="h-[19px] text-[10px]">
                              {event.category}
                            </Badge>
                            {event.severity === "critical" && (
                              <Badge tone="danger" className="h-[19px] text-[10px]">
                                Critical
                              </Badge>
                            )}
                            <span className="ml-auto hidden items-center gap-0.5 text-[10.5px] text-ink-3 sm:flex">
                              <MapPin className="h-2.5 w-2.5" />
                              {event.location ?? "Digital source"}
                            </span>
                          </div>

                          <p className="mt-1.5 text-[12px] leading-relaxed text-ink-2">{event.description}</p>

                          <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line pt-2.5">
                            <span className="flex items-center gap-1.5">
                              <span className="flex -space-x-1.5">
                                {linkedPeople.map((p) => (
                                  <PersonAvatar key={p.id} person={p} size="xs" ring />
                                ))}
                              </span>
                              <span className="flex items-center gap-1 text-[10.5px] text-ink-2">
                                {linkedPeople.map((p) => p.name.split(" ")[0]).join(", ")}
                              </span>
                            </span>

                            <span className="flex min-w-0 flex-wrap items-center gap-1">
                              {sources.map((item) => (
                                <button
                                  key={item.id}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openEvidence(item.id);
                                  }}
                                  className="flex max-w-[220px] items-center gap-1.5 rounded-md border border-line bg-surface-2 py-0.5 pl-0.5 pr-1.5 transition-colors hover:border-line-strong hover:bg-surface-3"
                                  title={item.name}
                                >
                                  <FileTypeTile type={item.type} size="sm" />
                                  <span className="truncate text-[10px] text-ink-2">{item.name}</span>
                                </button>
                              ))}
                              {sources.length === 0 && (
                                <span className="text-[10px] text-ink-3">No supporting file</span>
                              )}
                            </span>
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
