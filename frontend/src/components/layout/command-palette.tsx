import {
  ArrowUpRight,
  CalendarClock,
  CornerDownLeft,
  FolderClosed,
  LayoutGrid,
  Network,
  Search,
  Sparkles,
  FileText,
  ScrollText,
  Settings,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useApp, type View } from "@/store/app-store";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { PersonAvatar } from "@/components/person-avatar";
import { FileTypeTile } from "@/components/evidence/file-type";
import { formatDate, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const pages: { id: View; label: string; icon: typeof LayoutGrid }[] = [
  { id: "overview", label: "Overview", icon: LayoutGrid },
  { id: "vault", label: "Evidence Vault", icon: FolderClosed },
  { id: "timeline", label: "Incident Timeline", icon: CalendarClock },
  { id: "people", label: "People & Connections", icon: Network },
  { id: "assistant", label: "AI Assistant", icon: Sparkles },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "audit", label: "Audit Logs", icon: ScrollText },
  { id: "settings", label: "Settings", icon: Settings },
];

interface Result {
  key: string;
  group: string;
  label: string;
  meta?: string;
  icon?: React.ReactNode;
  run: () => void;
}

export function CommandPalette() {
  const {
    searchOpen,
    setSearchOpen,
    evidence,
    people,
    events,
    navigate,
    openEvidence,
    selectPerson,
  } = useApp();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!searchOpen) {
      setQuery("");
      setCursor(0);
    }
  }, [searchOpen]);

  const results = useMemo<Result[]>(() => {
    const q = query.trim().toLowerCase();
    const close = () => setSearchOpen(false);

    const pageResults = pages
      .filter((p) => !q || p.label.toLowerCase().includes(q))
      .map((p) => ({
        key: `page-${p.id}`,
        group: "Go to",
        label: p.label,
        icon: <p.icon className="h-4 w-4 text-ink-3" />,
        run: () => {
          navigate(p.id);
          close();
        },
      }));

    const evidenceResults = evidence
      .filter(
        (e) =>
          !q ||
          e.name.toLowerCase().includes(q) ||
          e.tags.some((t) => t.toLowerCase().includes(q)) ||
          people.some((p) => e.personIds.includes(p.id) && p.name.toLowerCase().includes(q)),
      )
      .slice(0, q ? 5 : 3)
      .map((e) => ({
        key: e.id,
        group: "Evidence",
        label: e.name,
        meta: `${e.type.toUpperCase()} · ${formatDate(e.uploadedAt)}`,
        icon: <FileTypeTile type={e.type} size="sm" />,
        run: () => {
          openEvidence(e.id);
          close();
        },
      }));

    const peopleResults = people
      .filter((p) => !q || p.name.toLowerCase().includes(q) || p.role.toLowerCase().includes(q))
      .slice(0, q ? 4 : 2)
      .map((p) => ({
        key: p.id,
        group: "People",
        label: p.name,
        meta: p.role,
        icon: <PersonAvatar person={p} size="sm" />,
        run: () => {
          navigate("people");
          selectPerson(p.id);
          close();
        },
      }));

    const eventResults = events
      .filter((e) => q && (e.title.toLowerCase().includes(q) || e.description.toLowerCase().includes(q)))
      .slice(0, 4)
      .map((e) => ({
        key: e.id,
        group: "Timeline",
        label: e.title,
        meta: `${formatDate(e.at)} · ${formatTime(e.at)}`,
        icon: (
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-3">
            <CalendarClock className="h-3.5 w-3.5 text-ink-2" />
          </span>
        ),
        run: () => {
          navigate("timeline");
          close();
        },
      }));

    return [...pageResults, ...evidenceResults, ...peopleResults, ...eventResults];
  }, [query, evidence, people, events, navigate, openEvidence, selectPerson, setSearchOpen]);

  useEffect(() => setCursor(0), [query]);

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-index="${cursor}"]`)?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  const groups = useMemo(() => {
    const map = new Map<string, (Result & { index: number })[]>();
    results.forEach((r, index) => {
      const bucket = map.get(r.group) ?? [];
      bucket.push({ ...r, index });
      map.set(r.group, bucket);
    });
    return [...map.entries()];
  }, [results]);

  return (
    <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
      <DialogContent
        className="top-[13vh] max-w-[580px] translate-y-0 overflow-hidden p-0"
        hideClose
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogTitle className="sr-only">Search workspace</DialogTitle>
        <div className="flex items-center gap-2.5 border-b border-line px-4">
          <Search className="h-4 w-4 shrink-0 text-ink-3" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search evidence, people, events…"
            aria-label="Search evidence, people and events"
            className="h-12 w-full bg-transparent text-[13.5px] outline-none placeholder:text-ink-3"
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setCursor((c) => Math.min(results.length - 1, c + 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setCursor((c) => Math.max(0, c - 1));
              } else if (e.key === "Enter" && results[cursor]) {
                e.preventDefault();
                results[cursor].run();
              }
            }}
          />
          <kbd className="hidden shrink-0 rounded border border-line bg-surface-2 px-1.5 py-0.5 font-sans text-[10px] text-ink-3 sm:block">
            ESC
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[52vh] overflow-y-auto p-2">
          {results.length === 0 && (
            <div className="px-4 py-10 text-center">
              <p className="text-[13px] font-medium">No results for “{query}”</p>
              <p className="mt-1 text-[12px] text-ink-2">
                Try a file name, a person, or a date such as “November 10”.
              </p>
            </div>
          )}
          {groups.map(([group, items]) => (
            <div key={group} className="mb-1">
              <p className="px-2.5 pb-1 pt-2 text-[10.5px] font-medium text-ink-3">
                {group}
              </p>
              {items.map((item) => (
                <button
                  key={item.key}
                  data-index={item.index}
                  onClick={item.run}
                  onMouseEnter={() => setCursor(item.index)}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-[7px] px-2.5 py-1.5 text-left transition-colors",
                    cursor === item.index ? "bg-surface-3" : "hover:bg-surface-2",
                  )}
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center">{item.icon}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12.5px] font-medium">{item.label}</span>
                    {item.meta && <span className="block truncate font-mono text-[9.5px] text-ink-3">{item.meta}</span>}
                  </span>
                  {cursor === item.index ? (
                    <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-ink-3" />
                  ) : (
                    <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-ink-3 opacity-0" />
                  )}
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4 border-t border-line bg-surface-2 px-4 py-2 font-mono text-[9px] text-ink-3">
          <span className="inline-flex items-center gap-1">
            <kbd className="rounded border border-line bg-surface px-1 font-sans">↑</kbd>
            <kbd className="rounded border border-line bg-surface px-1 font-sans">↓</kbd> navigate
          </span>
          <span className="inline-flex items-center gap-1">
            <kbd className="rounded border border-line bg-surface px-1 font-sans">↵</kbd> open
          </span>
          <span className="ml-auto">{results.length} results</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
