import {
  ArrowUpRight,
  CalendarDays,
  ChevronRight,
  CircleAlert,
  Clock3,
  FileStack,
  Link2,
  Plus,
  RefreshCw,
  ScanLine,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { useApp } from "@/store/app-store";
import { api, type EvidenceAiSummary } from "@/lib/api";
import type { Insight, PipelineStage } from "@/data/types";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { PersonAvatar, AvatarStack } from "@/components/person-avatar";
import { FileTypeTile, StatusBadge } from "@/components/evidence/file-type";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { formatBytes, formatDate, formatTime, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const kindMeta = {
  link: { label: "Connection", icon: Link2, tone: "violet" as const },
  anomaly: { label: "Anomaly", icon: CircleAlert, tone: "danger" as const },
  pattern: { label: "Pattern", icon: ScanLine, tone: "warning" as const },
  summary: { label: "Summary", icon: Sparkles, tone: "accent" as const },
};

export function DashboardPage() {
  const { evidence, people, events, insights, navigate, openEvidence, selectPerson, ask, workspace, activeWorkspaceId } = useApp();
  const [activeInsight, setActiveInsight] = useState<Insight | null>(null);
  const [summary, setSummary] = useState<EvidenceAiSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const latestEvidence = useMemo(
    () => [...evidence].sort((a, b) => +new Date(b.uploadedAt) - +new Date(a.uploadedAt))[0],
    [evidence],
  );
  const latestId = latestEvidence?.id;

  useEffect(() => {
    if (!latestId) {
      setSummary(null);
      return;
    }
    let cancelled = false;
    setSummaryLoading(true);
    void api
      .evidenceSummary(latestId)
      .then((result) => {
        if (!cancelled) setSummary(result);
      })
      .catch(() => {
        if (!cancelled) setSummary(null);
      })
      .finally(() => {
        if (!cancelled) setSummaryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [latestId, activeWorkspaceId]);

  const refreshSummary = async () => {
    if (!latestId) return;
    setSummaryLoading(true);
    try {
      setSummary(await api.evidenceSummary(latestId, true));
    } catch {
      // keep the previous summary on failure
    } finally {
      setSummaryLoading(false);
    }
  };

  const recentEvidence = useMemo(
    () => [...evidence].sort((a, b) => +new Date(b.uploadedAt) - +new Date(a.uploadedAt)).slice(0, 5),
    [evidence],
  );
  const recentEvents = useMemo(
    () => [...events].sort((a, b) => +new Date(a.at) - +new Date(b.at)).slice(-4),
    [events],
  );
  const featuredPeople = useMemo(
    () => people.filter((p) => p.role !== "Legal counsel").slice(0, 4),
    [people],
  );
  const pendingReviews = evidence.filter((e) => e.status === "review" || e.status === "failed").length;
  const highRisk = people.filter((p) => p.risk === "high").length;
  const last48h = evidence.filter((e) => Date.now() - +new Date(e.uploadedAt) < 48 * 3600 * 1000).length;
  const criticalEvents = events.filter((e) => e.severity === "critical").length;
  const mismatches = evidence.filter((e) => e.integrity === "mismatch").length;
  const processingCount = evidence.filter((e) => e.status === "processing" || e.status === "queued").length;
  const searchable = evidence.filter((e) => e.status === "processed").length;

  const intakeSeries = useMemo(() => {
    const series: { day: string; files: number }[] = [];
    for (let offset = 6; offset >= 0; offset -= 1) {
      const date = new Date();
      date.setDate(date.getDate() - offset);
      const key = date.toISOString().slice(0, 10);
      series.push({
        day: date.toLocaleDateString(undefined, { day: "2-digit", month: "short" }),
        files: evidence.filter((item) => item.uploadedAt.slice(0, 10) === key).length,
      });
    }
    return series;
  }, [evidence]);

  const pipeline = useMemo<PipelineStage[]>(() => {
    const total = evidence.length;
    const ratio = (done: number) => (total ? Math.round((done / total) * 100) : 0);
    return [
      {
        label: "Preserved",
        detail: `${total} items`,
        progress: total ? 100 : 0,
        state: total ? "done" : "queued",
      },
      {
        label: "Text extraction",
        detail: `${searchable} complete`,
        progress: ratio(searchable),
        state: processingCount > 0 ? "active" : total > 0 && searchable === total ? "done" : "queued",
      },
      {
        label: "Search index",
        detail: `${searchable} searchable`,
        progress: ratio(searchable),
        state: processingCount > 0 ? "active" : total > 0 && searchable === total ? "done" : "queued",
      },
      {
        label: "Entity links",
        detail: `${people.length} people`,
        progress: people.length ? 100 : 0,
        state: people.length ? "done" : "queued",
      },
      {
        label: "Timeline",
        detail: `${events.length} events`,
        progress: events.length ? 100 : 0,
        state: events.length ? "done" : "queued",
      },
    ];
  }, [evidence, events.length, people.length, processingCount, searchable]);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={
          <>
            <Badge tone="neutral" className="font-mono text-[10.5px] tracking-tight">
              {workspace.caseId}
            </Badge>
            <Badge tone="success" dot>
              Active investigation
            </Badge>
          </>
        }
        title={workspace.caseName}
        description={
          evidence.length
            ? `${evidence.length} preserved items across ${people.length} people and ${events.length} timeline events.`
            : "No evidence preserved yet. Upload a file to begin."
        }
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate("assistant")}>
              <Sparkles className="h-3.5 w-3.5 text-accent" /> Ask AI
            </Button>
            <Button variant="primary" onClick={() => navigate("vault")}>
              <Plus className="h-4 w-4" /> Add evidence
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Total evidence"
          value={evidence.length}
          footnote={`${last48h} added in the last 48 hours`}
          trend={last48h ? `+${last48h}` : undefined}
          icon={FileStack}
          tint="#007AFF"
        />
        <StatCard
          label="People identified"
          value={people.length}
          footnote={`${highRisk} high-risk`}
          icon={Users}
          tint="#5E5CE6"
        />
        <StatCard
          label="Events detected"
          value={events.length}
          footnote={`${criticalEvents} critical events`}
          icon={CalendarDays}
          tint="#FF9F0A"
        />
        <StatCard
          label="Pending reviews"
          value={pendingReviews}
          footnote={`${mismatches} integrity mismatch${mismatches === 1 ? "" : "es"}`}
          icon={ShieldAlert}
          tint="#FF3B30"
        />
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-12">
        <Card className="lg:col-span-8">
          <CardHeader>
            <div>
              <CardTitle>Recent evidence</CardTitle>
              <p className="mt-0.5 text-[11.5px] text-ink-2">Newest preserved items across all sources</p>
            </div>
            <button
              onClick={() => navigate("vault")}
              className="inline-flex items-center gap-0.5 text-[11.5px] font-medium text-accent hover:underline"
            >
              View all <ChevronRight className="h-3 w-3" />
            </button>
          </CardHeader>
          <CardContent className="mt-3 px-2 pb-2">
            <ul className="divide-y divide-line">
              {recentEvidence.map((item) => (
                <li key={item.id}>
                  <button
                    onClick={() => openEvidence(item.id)}
                    className="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-surface-2"
                  >
                    <FileTypeTile type={item.type} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[12.5px] font-medium">{item.name}</span>
                      <span className="mt-0.5 flex items-center gap-1.5 text-[10.5px] text-ink-3">
                        {formatBytes(item.size)}
                        <span className="h-0.5 w-0.5 rounded-full bg-ink-3" />
                        {item.source}
                      </span>
                    </span>
                    <span className="hidden items-center gap-1.5 sm:flex">
                      <AvatarStack
                        people={people.filter((p) => item.personIds.includes(p.id))}
                        max={3}
                      />
                    </span>
                    <span className="hidden w-[104px] justify-end md:flex">
                      <StatusBadge status={item.status} />
                    </span>
                    <span className="hidden w-[58px] text-right text-[10.5px] text-ink-3 sm:block">
                      {timeAgo(item.uploadedAt)}
                    </span>
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 text-ink-3 opacity-0 transition-opacity group-hover:opacity-100" />
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card className="lg:col-span-4">
          <CardHeader>
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              <CardTitle>{insights.length ? "AI insights" : "Latest evidence"}</CardTitle>
            </div>
            <Badge tone="accent">
              {insights.length
                ? `${insights.filter((i) => !i.reviewed).length} new`
                : summary?.mode === "ai"
                  ? "AI summary"
                  : "Summary"}
            </Badge>
          </CardHeader>
          <CardContent className="mt-2 space-y-1 px-2 pb-2">
            {insights.length === 0 &&
              (latestEvidence ? (
                <div className="px-2 pb-1">
                  <div className="flex items-center gap-2">
                    <FileTypeTile type={latestEvidence.type} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[12px] font-medium">{latestEvidence.name}</p>
                      <p className="text-[10px] text-ink-3">
                        {timeAgo(latestEvidence.uploadedAt)} · newest upload
                      </p>
                    </div>
                  </div>
                  <div className="mt-2 max-h-40 overflow-y-auto rounded-lg bg-surface-2 p-2.5 text-[11.5px] leading-relaxed text-ink-2">
                    {summaryLoading
                      ? "Summarising evidence…"
                      : summary?.summary ?? "No summary is available for this item yet."}
                  </div>
                  {summary?.limitations && summary.limitations.length > 0 && (
                    <p className="mt-1 line-clamp-2 text-[10px] text-ink-3">{summary.limitations[0]}</p>
                  )}
                  <div className="mt-2 flex items-center justify-between">
                    <button
                      onClick={() => openEvidence(latestEvidence.id)}
                      className="text-[11px] font-medium text-accent hover:underline"
                    >
                      Open evidence
                    </button>
                    <button
                      onClick={() => void refreshSummary()}
                      className="flex items-center gap-1 text-[10.5px] text-ink-3 transition-colors hover:text-ink"
                    >
                      <RefreshCw className={cn("h-3 w-3", summaryLoading && "animate-spin")} /> Refresh
                    </button>
                  </div>
                </div>
              ) : (
                <p className="px-3 py-6 text-center text-[11.5px] leading-relaxed text-ink-3">
                  Upload evidence to see an AI summary of your newest file here.
                </p>
              ))}
            {insights.slice(0, 3).map((insight) => {
              const meta = kindMeta[insight.kind];
              return (
                <button
                  key={insight.id}
                  onClick={() => setActiveInsight(insight)}
                  className="w-full rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-surface-2"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "flex h-5 w-5 items-center justify-center rounded-md",
                        insight.severity === "critical"
                          ? "bg-danger/10 text-danger"
                          : insight.severity === "warning"
                            ? "bg-warning/12 text-warning"
                            : "bg-accent-soft text-accent",
                      )}
                    >
                      <meta.icon className="h-3 w-3" />
                    </span>
                    <span className="truncate text-[12px] font-medium">{insight.title}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 pl-7 text-[11.5px] leading-relaxed text-ink-2">{insight.body}</p>
                  <div className="mt-1.5 flex items-center gap-2 pl-7">
                    <span className="text-[10px] text-ink-3">{meta.label}</span>
                    <span className="h-0.5 w-0.5 rounded-full bg-ink-3" />
                    <span className="text-[10px] font-medium text-ink-2">{insight.confidence}% confidence</span>
                    {!insight.reviewed && <span className="h-1 w-1 rounded-full bg-accent" />}
                  </div>
                </button>
              );
            })}
            {insights.length > 0 && (
              <button
                onClick={() => navigate("assistant")}
                className="mt-1 flex w-full items-center justify-center gap-1 rounded-lg py-2 text-[11.5px] font-medium text-accent transition-colors hover:bg-accent-soft"
              >
                Investigate with AI <ArrowUpRight className="h-3 w-3" />
              </button>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-8">
          <CardHeader>
            <div>
              <CardTitle>Incident timeline</CardTitle>
              <p className="mt-0.5 text-[11.5px] text-ink-2">Latest reconstructed events</p>
            </div>
            <button
              onClick={() => navigate("timeline")}
              className="inline-flex items-center gap-0.5 text-[11.5px] font-medium text-accent hover:underline"
            >
              Open timeline <ChevronRight className="h-3 w-3" />
            </button>
          </CardHeader>
          <CardContent className="mt-3">
            <ol className="relative ml-1.5 border-l border-line pl-4">
              {recentEvents.map((event) => (
                <li key={event.id} className="relative pb-4 last:pb-0">
                  <span
                    className={cn(
                      "absolute -left-[21.5px] top-1 h-2 w-2 rounded-full ring-[3px] ring-surface",
                      event.severity === "critical"
                        ? "bg-danger"
                        : event.severity === "warning"
                          ? "bg-warning"
                          : "bg-accent",
                    )}
                  />
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="text-[11px] font-medium tabular-nums text-ink-3">
                      {formatDate(event.at)} · {formatTime(event.at)}
                    </span>
                    <Badge tone="neutral" className="h-[18px] text-[10px]">
                      {event.category}
                    </Badge>
                    <span className="ml-auto hidden text-[10.5px] text-ink-3 sm:block">
                      {event.evidenceIds.length} source{event.evidenceIds.length === 1 ? "" : "s"}
                    </span>
                  </div>
                  <button
                    onClick={() => event.evidenceIds[0] && openEvidence(event.evidenceIds[0])}
                    className="group mt-0.5 flex w-full items-start gap-2 text-left"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block text-[12.5px] font-medium transition-colors group-hover:text-accent">
                        {event.title}
                      </span>
                      <span className="mt-0.5 line-clamp-1 block text-[11.5px] text-ink-2">
                        {event.description}
                      </span>
                    </span>
                    <ArrowUpRight className="mt-0.5 h-3 w-3 shrink-0 text-ink-3 opacity-0 transition-opacity group-hover:opacity-100" />
                  </button>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>

        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle>Processing status</CardTitle>
            <Badge tone="accent" dot>
              {processingCount} active
            </Badge>
          </CardHeader>
          <CardContent className="mt-3 space-y-3">
            {pipeline.slice(0, 5).map((stage) => (
              <div key={stage.label}>
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="truncate text-[11.5px] font-medium">{stage.label}</span>
                  <span
                    className={cn(
                      "shrink-0 text-[10px] font-medium",
                      stage.state === "done" ? "text-success" : "text-ink-2",
                    )}
                  >
                    {stage.state === "done" ? "Complete" : `${stage.progress}%`}
                  </span>
                </div>
                <Progress value={stage.progress} tone={stage.state === "done" ? "success" : "accent"} />
              </div>
            ))}
            <button
              onClick={() => navigate("vault")}
              className="flex w-full items-center justify-between rounded-lg border border-line px-3 py-2 text-left transition-colors hover:bg-surface-2"
            >
              <span className="text-[11px] text-ink-2">
                {evidence.filter((e) => e.status === "processed").length} of {evidence.length} files searchable
              </span>
              <ChevronRight className="h-3 w-3 text-ink-3" />
            </button>
          </CardContent>
        </Card>

        <Card className="lg:col-span-7">
          <CardHeader>
            <div>
              <CardTitle>Recently identified people</CardTitle>
              <p className="mt-0.5 text-[11.5px] text-ink-2">Linked through metadata and conversation</p>
            </div>
            <button
              onClick={() => navigate("people")}
              className="inline-flex items-center gap-0.5 text-[11.5px] font-medium text-accent hover:underline"
            >
              View graph <ChevronRight className="h-3 w-3" />
            </button>
          </CardHeader>
          <CardContent className="mt-3 grid gap-2 sm:grid-cols-2">
            {featuredPeople.map((person) => (
              <button
                key={person.id}
                onClick={() => {
                  selectPerson(person.id);
                  navigate("people");
                }}
                className="flex items-center gap-2.5 rounded-xl border border-line px-3 py-2.5 text-left transition-colors hover:bg-surface-2"
              >
                <PersonAvatar person={person} size="lg" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[12.5px] font-medium">{person.name}</span>
                  <span className="mt-0.5 block truncate text-[10.5px] text-ink-2">{person.role}</span>
                  <span className="mt-1 flex items-center gap-1.5 text-[10px] text-ink-3">
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        person.risk === "high"
                          ? "bg-danger"
                          : person.risk === "medium"
                            ? "bg-warning"
                            : "bg-success",
                      )}
                    />
                    {person.risk} risk · {person.evidenceCount} files
                  </span>
                </span>
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-ink-3" />
              </button>
            ))}
          </CardContent>
        </Card>

        <Card className="lg:col-span-5">
          <CardHeader>
            <div>
              <CardTitle>Evidence intake</CardTitle>
              <p className="mt-0.5 text-[11.5px] text-ink-2">Files preserved per day</p>
            </div>
            <Badge tone="neutral">
              <Clock3 className="mr-0.5 h-3 w-3" /> 7 days
            </Badge>
          </CardHeader>
          <CardContent className="mt-2 px-3 pb-3">
            <div className="h-[132px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={intakeSeries} margin={{ top: 8, right: 4, left: -28, bottom: 0 }} barCategoryGap={18}>
                  <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 9.5, fill: "var(--text-3)" }}
                    axisLine={false}
                    tickLine={false}
                    dy={4}
                  />
                  <Tooltip
                    cursor={{ fill: "var(--surface-3)", radius: 3 }}
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--line)",
                      borderRadius: 10,
                      fontSize: 11,
                      boxShadow: "var(--shadow-pop)",
                      padding: "6px 10px",
                    }}
                    labelStyle={{ color: "var(--text-2)", fontSize: 10, marginBottom: 2 }}
                    itemStyle={{ color: "var(--text)" }}
                    formatter={(value) => [`${value} files`, "Preserved"]}
                  />
                  <Bar dataKey="files" fill="var(--accent)" radius={[4, 4, 2, 2]} maxBarSize={22} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-1 flex items-center justify-between border-t border-line pt-2.5">
              <span className="text-[11px] text-ink-2">Total this week</span>
              <span className="text-[11.5px] font-semibold tabular-nums">
                {intakeSeries.reduce((sum, d) => sum + d.files, 0)} files
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <InsightDialog insight={activeInsight} onClose={() => setActiveInsight(null)} ask={ask} openEvidence={openEvidence} navigate={navigate} />
    </div>
  );
}

function InsightDialog({
  insight,
  onClose,
  ask,
  openEvidence,
  navigate,
}: {
  insight: Insight | null;
  onClose: () => void;
  ask: (q: string) => void;
  openEvidence: (id: string) => void;
  navigate: (view: "assistant") => void;
}) {
  const { evidence, reviewInsight } = useApp();
  if (!insight) return null;
  const meta = kindMeta[insight.kind];
  const refs = evidence.filter((e) => insight.evidenceIds.includes(e.id));

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="p-5">
        <DialogTitle className="pr-8 text-[16px] font-semibold tracking-[-0.01em]">{insight.title}</DialogTitle>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge tone={meta.tone}>
            <meta.icon className="mr-0.5 h-3 w-3" /> {meta.label}
          </Badge>
          <Badge tone={insight.severity === "critical" ? "danger" : insight.severity === "warning" ? "warning" : "neutral"} className="capitalize">
            {insight.severity}
          </Badge>
          <span className="text-[11px] text-ink-3">
            {insight.confidence}% confidence · {timeAgo(insight.createdAt)}
          </span>
        </div>
        <p className="mt-3 text-[13px] leading-relaxed text-ink-2">{insight.body}</p>

        <p className="mb-1.5 mt-4 text-[10.5px] font-medium uppercase tracking-[0.05em] text-ink-3">
          Supporting evidence
        </p>
        <ul className="space-y-1">
          {refs.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => {
                  onClose();
                  openEvidence(item.id);
                }}
                className="flex w-full items-center gap-2 rounded-lg border border-line px-2 py-1.5 text-left transition-colors hover:bg-surface-2"
              >
                <FileTypeTile type={item.type} size="sm" />
                <span className="min-w-0 flex-1 truncate text-[11.5px]">{item.name}</span>
                <ChevronRight className="h-3 w-3 text-ink-3" />
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-4 flex items-center gap-2">
          <Button
            variant="primary"
            className="flex-1"
            onClick={() => {
              reviewInsight(insight.id);
              ask(`Summarize the finding: ${insight.title}`);
              navigate("assistant");
              onClose();
            }}
          >
            <Sparkles className="h-3.5 w-3.5" /> Discuss with assistant
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              reviewInsight(insight.id);
              onClose();
            }}
          >
            Mark reviewed
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
