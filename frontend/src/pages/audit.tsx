import {
  Check,
  Download,
  KeyRound,
  ScrollText,
  ShieldAlert,
  Search,
  UserRound,
  Ban,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useApp } from "@/store/app-store";
import { workspace } from "@/lib/workspace";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SearchInput } from "@/components/ui/input";
import { StatCard } from "@/components/stat-card";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDate, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const resultTone = {
  success: "success",
  warning: "warning",
  denied: "danger",
} as const;

const resultLabel = {
  success: "Success",
  warning: "Review",
  denied: "Denied",
} as const;

export function AuditPage() {
  const { auditLogs, toast, evidence } = useApp();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<"all" | "success" | "warning" | "denied">("all");
  const [actor, setActor] = useState("all");

  const actors = useMemo(() => [...new Set(auditLogs.map((a) => a.actor))], [auditLogs]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return auditLogs.filter((entry) => {
      if (result !== "all" && entry.result !== result) return false;
      if (actor !== "all" && entry.actor !== actor) return false;
      if (!q) return true;
      return (
        entry.action.toLowerCase().includes(q) ||
        entry.target.toLowerCase().includes(q) ||
        entry.actor.toLowerCase().includes(q) ||
        entry.ip.includes(q)
      );
    });
  }, [auditLogs, query, result, actor]);

  const exportCsv = () => {
    const header = ["id", "timestamp", "actor", "action", "target", "ip", "result"];
    const rows = filtered.map((a) => [a.id, a.at, a.actor, a.action, a.target, a.ip, a.result]);
    const csv = [header, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `veritas-audit-log-${workspace.caseId.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
    toast("Audit log exported", `${filtered.length} entries · CSV with hash manifest reference.`, "success");
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={
          <>
            <Badge tone="success" dot>
              Ledger intact
            </Badge>
            <span className="text-[11px] text-ink-3">Retention 7 years · immutable</span>
          </>
        }
        title="Audit Logs"
        description="Every access, upload, inference and export is recorded. Entries are append-only and tied to the custody ledger."
        actions={
          <Button variant="secondary" onClick={exportCsv}>
            <Download className="h-3.5 w-3.5" /> Export CSV
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Recorded actions" value={auditLogs.length} footnote="Across 5 actors and 1 service" icon={ScrollText} tint="#007AFF" />
        <StatCard label="Integrity events" value={auditLogs.filter((a) => a.result === "warning").length} footnote="1 mismatch · 1 relationship inferred" icon={ShieldAlert} tint="#FF9F0A" />
        <StatCard label="Denied attempts" value={auditLogs.filter((a) => a.result === "denied").length} footnote="Blocked at workspace edge" icon={Ban} tint="#FF3B30" />
        <StatCard label="Evidence under custody" value={evidence.length} footnote="13 verified · 1 excluded" icon={KeyRound} tint="#34C759" />
      </div>

      <div className="mt-3 rounded-card border border-line bg-surface shadow-card">
        <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
          <SearchInput
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search actor, action, target or IP…"
            className="w-full sm:w-[290px]"
            aria-label="Search audit log"
          />
          <div className="flex items-center gap-1">
            {(["all", "success", "warning", "denied"] as const).map((value) => (
              <button
                key={value}
                onClick={() => setResult(value)}
                aria-pressed={result === value}
                className={cn(
                  "h-7 rounded-full px-2.5 text-[11px] font-medium capitalize transition-colors",
                  result === value
                    ? "bg-ink text-surface"
                    : "bg-surface-2 text-ink-2 hover:bg-surface-3 hover:text-ink",
                )}
              >
                {value === "all" ? "All results" : value}
              </button>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <UserRound className="h-3 w-3 text-ink-3" />
            <select
              value={actor}
              onChange={(e) => setActor(e.target.value)}
              aria-label="Filter by actor"
              className="h-8 max-w-[160px] rounded-lg border border-line bg-surface px-2 text-[11.5px] text-ink-2 outline-none"
            >
              <option value="all">Any actor</option>
              {actors.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            {(query || result !== "all" || actor !== "all") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setQuery("");
                  setResult("all");
                  setActor("all");
                }}
              >
                Clear
              </Button>
            )}
          </div>
        </div>

        {filtered.length === 0 ? (
          <EmptyState icon={Search} title="No matching entries" description="Try a different actor, result or search term." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse">
              <thead>
                <tr className="border-b border-line text-left text-[10.5px] font-medium text-ink-3">
                  <th className="py-2 pl-4 pr-2 font-medium">Timestamp</th>
                  <th className="px-2 py-2 font-medium">Actor</th>
                  <th className="px-2 py-2 font-medium">Action</th>
                  <th className="px-2 py-2 font-medium">Target</th>
                  <th className="hidden px-2 py-2 font-medium md:table-cell">Source IP</th>
                  <th className="px-4 py-2 text-right font-medium">Result</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((entry) => (
                  <tr key={entry.id} className="border-b border-line/70 last:border-0 hover:bg-surface-2">
                    <td className="whitespace-nowrap py-2 pl-4 pr-2 text-[11px] tabular-nums text-ink-2">
                      {formatDate(entry.at)}
                      <span className="ml-1.5 text-ink-3">{formatTime(entry.at)}</span>
                    </td>
                    <td className="px-2 py-2">
                      <span className="flex items-center gap-1.5 text-[11px]">
                        <span
                          className={cn(
                            "flex h-5 w-5 items-center justify-center rounded-full text-[8.5px] font-semibold",
                            entry.actor === "System"
                              ? "bg-surface-3 text-ink-2"
                              : entry.actor === "Unknown"
                                ? "bg-danger/10 text-danger"
                                : "bg-accent-soft text-accent",
                          )}
                        >
                          {entry.actor === "System" ? (
                            <Check className="h-2.5 w-2.5" />
                          ) : (
                            entry.actor.slice(0, 1)
                          )}
                        </span>
                        {entry.actor}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-[11px] font-medium">{entry.action}</td>
                    <td className="max-w-[280px] truncate px-2 py-2 text-[11px] text-ink-2" title={entry.target}>
                      {entry.target}
                    </td>
                    <td className="hidden px-2 py-2 font-mono text-[10.5px] text-ink-3 md:table-cell">{entry.ip}</td>
                    <td className="px-4 py-2 text-right">
                      <Badge tone={resultTone[entry.result]} dot>
                        {resultLabel[entry.result]}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2.5 text-[10.5px] text-ink-3">
          <span>
            Showing {filtered.length} of {auditLogs.length} entries
          </span>
          <span className="inline-flex items-center gap-1.5 font-mono">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            last digest 9f2c74e1…5a9f6c
          </span>
        </div>
      </div>
    </div>
  );
}
