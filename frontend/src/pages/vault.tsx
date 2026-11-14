import {
  ArrowDownUp,
  ChevronRight,
  CloudUpload,
  FileStack,
  FolderClosed,
  Grid2X2,
  List,
  Plus,
  Search,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { useApp } from "@/store/app-store";
import type { EvidenceStatus, EvidenceType } from "@/data/types";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SearchInput } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/ui/empty-state";
import { PersonAvatar } from "@/components/person-avatar";
import { FileTypeTile, StatusBadge, typeMeta } from "@/components/evidence/file-type";
import { formatBytes, formatDate, timeAgo, truncateHash } from "@/lib/format";
import { cn } from "@/lib/utils";

const typeFilters: { value: "all" | EvidenceType; label: string }[] = [
  { value: "all", label: "All" },
  { value: "image", label: "Images" },
  { value: "document", label: "PDFs" },
  { value: "audio", label: "Audio" },
  { value: "video", label: "Video" },
  { value: "chat", label: "Chat" },
  { value: "data", label: "Data" },
];

export function VaultPage() {
  const { evidence, people, uploadFiles, openEvidence, uploads, toast } = useApp();
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | EvidenceType>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | EvidenceStatus>("all");
  const [personFilter, setPersonFilter] = useState("all");
  const [layout, setLayout] = useState<"list" | "grid">("list");
  const [sort, setSort] = useState<"newest" | "oldest" | "name" | "size">("newest");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const prevent = (e: globalThis.DragEvent) => e.preventDefault();
    window.addEventListener("dragover", prevent);
    window.addEventListener("drop", prevent);
    return () => {
      window.removeEventListener("dragover", prevent);
      window.removeEventListener("drop", prevent);
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = evidence.filter((item) => {
      if (typeFilter !== "all" && item.type !== typeFilter) return false;
      if (statusFilter !== "all" && item.status !== statusFilter) return false;
      if (personFilter !== "all" && !item.personIds.includes(personFilter)) return false;
      if (!q) return true;
      return (
        item.name.toLowerCase().includes(q) ||
        item.source.toLowerCase().includes(q) ||
        item.tags.some((t) => t.toLowerCase().includes(q)) ||
        item.hash.includes(q) ||
        people.some((p) => item.personIds.includes(p.id) && p.name.toLowerCase().includes(q))
      );
    });
    return list.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "size") return b.size - a.size;
      if (sort === "oldest") return +new Date(a.uploadedAt) - +new Date(b.uploadedAt);
      return +new Date(b.uploadedAt) - +new Date(a.uploadedAt);
    });
  }, [evidence, people, query, typeFilter, statusFilter, personFilter, sort]);

  const activeFilters =
    (typeFilter !== "all" ? 1 : 0) + (statusFilter !== "all" ? 1 : 0) + (personFilter !== "all" ? 1 : 0);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    uploadFiles(Array.from(files));
    toast(
      files.length > 1 ? `${files.length} files queued` : "File queued",
      "Hashing and preserving the original before processing.",
    );
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const inFlight = evidence.filter((e) => e.id in uploads && uploads[e.id] < 100);

  return (
    <div
      className="animate-fade-in"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
      }}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        accept="image/*,application/pdf,audio/*,video/*,.txt,.csv,.json"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {dragging && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-accent/8 p-6 backdrop-blur-[2px]">
          <div className="flex w-full max-w-md flex-col items-center rounded-[20px] border-2 border-dashed border-accent bg-surface px-8 py-12 text-center shadow-pop">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent">
              <CloudUpload className="h-6 w-6" />
            </div>
            <p className="mt-3 text-[15px] font-semibold">Drop to preserve evidence</p>
            <p className="mt-1 text-[12.5px] text-ink-2">
              Files are hashed with SHA-256 before any processing begins.
            </p>
          </div>
        </div>
      )}

      <PageHeader
        title="Evidence Vault"
        description="Preserved originals and derived artifacts. Every item is hashed at intake and verified after processing."
        actions={
          <>
            <Button variant="secondary" onClick={() => toast("Vault sealed", "Chain-of-custody ledger is up to date.", "success")}>
              Verify vault
            </Button>
            <Button variant="primary" onClick={() => inputRef.current?.click()}>
              <Plus className="h-4 w-4" /> Upload evidence
            </Button>
          </>
        }
      />

      <button
        onClick={() => inputRef.current?.click()}
        className="group mb-3 flex w-full items-center gap-3 rounded-card border border-dashed border-line-strong bg-surface/60 px-4 py-3.5 text-left transition-colors hover:border-accent/50 hover:bg-accent-soft/30"
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-surface-3 text-ink-2 transition-colors group-hover:bg-accent-soft group-hover:text-accent">
          <CloudUpload className="h-4 w-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[12.5px] font-medium">Drag files here, or browse</span>
          <span className="mt-0.5 block text-[11px] text-ink-3">
            Images, PDFs, audio, video, chat exports · up to 2 GB per file
          </span>
        </span>
        <span className="hidden text-[11px] font-medium text-accent sm:block">Choose files</span>
      </button>

      {inFlight.length > 0 && (
        <div className="mb-3 space-y-2 rounded-card border border-accent/25 bg-accent-soft/40 p-3">
          {inFlight.map((item) => (
            <div key={item.id} className="flex items-center gap-2.5">
              <FileTypeTile type={item.type} size="sm" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-[11.5px] font-medium">{item.name}</span>
                  <span className="shrink-0 text-[10.5px] tabular-nums text-ink-2">{uploads[item.id]}%</span>
                </div>
                <Progress value={uploads[item.id]} className="mt-1 h-1" />
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-card border border-line bg-surface shadow-card">
        <div className="flex flex-col gap-2.5 border-b border-line p-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 text-[11.5px] text-ink-2">
              <FolderClosed className="h-3.5 w-3.5 text-ink-3" />
              <span>Vault</span>
              <ChevronRight className="h-3 w-3 text-ink-3" />
              <span className="font-medium text-ink">All evidence</span>
              <span className="text-ink-3">· {filtered.length}</span>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <div className="flex items-center rounded-lg border border-line p-0.5">
                <button
                  onClick={() => setLayout("list")}
                  aria-label="List view"
                  aria-pressed={layout === "list"}
                  className={cn(
                    "flex h-6 w-7 items-center justify-center rounded-md transition-colors",
                    layout === "list" ? "bg-surface-3 text-ink" : "text-ink-3 hover:text-ink",
                  )}
                >
                  <List className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => setLayout("grid")}
                  aria-label="Grid view"
                  aria-pressed={layout === "grid"}
                  className={cn(
                    "flex h-6 w-7 items-center justify-center rounded-md transition-colors",
                    layout === "grid" ? "bg-surface-3 text-ink" : "text-ink-3 hover:text-ink",
                  )}
                >
                  <Grid2X2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <label className="relative">
                <ArrowDownUp className="pointer-events-none absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-ink-3" />
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as typeof sort)}
                  aria-label="Sort evidence"
                  className="h-8 appearance-none rounded-lg border border-line bg-surface pl-7 pr-6 text-[11.5px] outline-none"
                >
                  <option value="newest">Newest</option>
                  <option value="oldest">Oldest</option>
                  <option value="name">Name</option>
                  <option value="size">Size</option>
                </select>
              </label>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <SearchInput
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search evidence…"
              className="w-full sm:w-[280px]"
              aria-label="Search evidence"
            />
            <div className="flex flex-wrap items-center gap-1">
              {typeFilters.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setTypeFilter(t.value)}
                  aria-pressed={typeFilter === t.value}
                  className={cn(
                    "h-7 rounded-full px-2.5 text-[11px] font-medium transition-colors",
                    typeFilter === t.value
                      ? "bg-ink text-surface"
                      : "bg-surface-2 text-ink-2 hover:bg-surface-3 hover:text-ink",
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <label className="relative">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
                  aria-label="Filter by status"
                  className="h-8 rounded-lg border border-line bg-surface px-2 text-[11.5px] text-ink-2 outline-none"
                >
                  <option value="all">Any status</option>
                  <option value="processed">Processed</option>
                  <option value="processing">Processing</option>
                  <option value="queued">Queued</option>
                  <option value="review">Needs review</option>
                  <option value="failed">Failed</option>
                </select>
              </label>
              <select
                value={personFilter}
                onChange={(e) => setPersonFilter(e.target.value)}
                aria-label="Filter by person"
                className="h-8 max-w-[150px] rounded-lg border border-line bg-surface px-2 text-[11.5px] text-ink-2 outline-none"
              >
                <option value="all">Any person</option>
                {people.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              {(activeFilters > 0 || query) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setQuery("");
                    setTypeFilter("all");
                    setStatusFilter("all");
                    setPersonFilter("all");
                  }}
                >
                  <X className="h-3 w-3" /> Clear
                </Button>
              )}
            </div>
          </div>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={FileStack}
            title="No evidence matches these filters"
            description="Try a broader search, or upload a new item to begin extraction."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setQuery("");
                  setTypeFilter("all");
                  setStatusFilter("all");
                  setPersonFilter("all");
                }}
              >
                Reset filters
              </Button>
            }
          />
        ) : layout === "list" ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-line text-left text-[10.5px] font-medium text-ink-3">
                  <th className="py-2 pl-4 pr-2 font-medium">Name</th>
                  <th className="hidden px-2 py-2 font-medium md:table-cell">People</th>
                  <th className="hidden px-2 py-2 font-medium lg:table-cell">Source</th>
                  <th className="hidden px-2 py-2 font-medium sm:table-cell">Size</th>
                  <th className="hidden px-2 py-2 font-medium md:table-cell">Uploaded</th>
                  <th className="px-2 py-2 font-medium">Status</th>
                  <th className="w-8 px-2 py-2" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const linked = people.filter((p) => item.personIds.includes(p.id));
                  const progress = uploads[item.id];
                  return (
                    <tr
                      key={item.id}
                      onClick={() => openEvidence(item.id)}
                      className="group cursor-pointer border-b border-line/70 transition-colors last:border-0 hover:bg-surface-2"
                    >
                      <td className="max-w-[190px] py-2.5 pl-4 pr-2 sm:max-w-[300px]">
                        <div className="flex items-center gap-2.5">
                          <FileTypeTile type={item.type} />
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openEvidence(item.id);
                            }}
                            className="min-w-0 text-left outline-offset-4"
                          >
                            <span className="block truncate text-[12.5px] font-medium">{item.name}</span>
                            <span className="mt-0.5 flex items-center gap-1.5 text-[10.5px] text-ink-3">
                              {typeMeta[item.type].label}
                              <span className="h-0.5 w-0.5 rounded-full bg-ink-3" />
                              <span className="font-mono">{truncateHash(item.hash, 8, 4)}</span>
                            </span>
                          </button>
                          {progress !== undefined && progress < 100 && (
                            <Progress value={progress} className="mt-1 h-1 w-24" />
                          )}
                        </div>
                      </td>
                      <td className="hidden px-2 py-2.5 md:table-cell">
                        <span className="flex items-center -space-x-1.5">
                          {linked.slice(0, 3).map((p) => (
                            <PersonAvatar key={p.id} person={p} size="sm" ring />
                          ))}
                          {linked.length === 0 && <span className="text-[11px] text-ink-3">—</span>}
                          {linked.length > 3 && (
                            <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-surface-3 text-[9.5px] font-medium text-ink-2 ring-2 ring-surface">
                              +{linked.length - 3}
                            </span>
                          )}
                        </span>
                      </td>
                      <td className="hidden max-w-[190px] truncate px-2 py-2.5 text-[11.5px] text-ink-2 lg:table-cell">
                        {item.source}
                      </td>
                      <td className="hidden whitespace-nowrap px-2 py-2.5 text-[11.5px] tabular-nums text-ink-2 sm:table-cell">
                        {formatBytes(item.size)}
                      </td>
                      <td className="hidden whitespace-nowrap px-2 py-2.5 text-[11.5px] text-ink-2 md:table-cell">
                        {timeAgo(item.uploadedAt)}
                      </td>
                      <td className="px-2 py-2.5">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-2 py-2.5">
                        <ChevronRight className="h-3.5 w-3.5 text-ink-3 opacity-0 transition-opacity group-hover:opacity-100" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid gap-2.5 p-3 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((item) => {
              const linked = people.filter((p) => item.personIds.includes(p.id));
              return (
                <button
                  key={item.id}
                  onClick={() => openEvidence(item.id)}
                  className="group flex flex-col rounded-xl border border-line bg-surface p-3 text-left transition-all duration-200 hover:border-line-strong hover:shadow-card"
                >
                  <div className="flex items-start gap-2.5">
                    <FileTypeTile type={item.type} size="lg" />
                    <div className="min-w-0 flex-1">
                      <p className="line-clamp-2 text-[12.5px] font-medium leading-snug">{item.name}</p>
                      <p className="mt-1 text-[10.5px] text-ink-3">
                        {typeMeta[item.type].label} · {formatBytes(item.size)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between border-t border-line pt-2.5">
                    <div className="flex items-center -space-x-1.5">
                      {linked.slice(0, 3).map((p) => (
                        <PersonAvatar key={p.id} person={p} size="xs" ring />
                      ))}
                      {linked.length === 0 && (
                        <span className="text-[10.5px] text-ink-3">{formatDate(item.uploadedAt)}</span>
                      )}
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                </button>
              );
            })}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2.5 text-[10.5px] text-ink-3">
          <span>
            {filtered.length} of {evidence.length} items · {formatBytes(evidence.reduce((s, e) => s + e.size, 0))} preserved
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            SHA-256 verified · 1 mismatch excluded
          </span>
        </div>
      </div>

      <p className="mt-3 flex items-center gap-1.5 text-[10.5px] text-ink-3">
        <Search className="h-3 w-3" /> Search matches file names, sources, tags, people and hash prefixes.
        <Badge tone="neutral" className="ml-1 h-[18px] text-[9.5px]">
          {evidence.length} items
        </Badge>
      </p>
    </div>
  );
}
