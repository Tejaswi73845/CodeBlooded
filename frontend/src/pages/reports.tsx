import {
  Check,
  CircleAlert,
  Download,
  FileCheck2,
  Fingerprint,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useApp } from "@/store/app-store";
import { api, type CaseAnalysis } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/segmented";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { formatBytes, formatDate, formatDateTime, formatTime, truncateHash } from "@/lib/format";
import { cn } from "@/lib/utils";

type SectionKey =
  | "summary"
  | "findings"
  | "chronology"
  | "people"
  | "evidence"
  | "integrity"
  | "relatedness";

const sectionLabels: { key: SectionKey; label: string }[] = [
  { key: "summary", label: "Incident summary" },
  { key: "findings", label: "Identified inconsistencies" },
  { key: "chronology", label: "Chronological events" },
  { key: "people", label: "People involved" },
  { key: "evidence", label: "Supporting evidence" },
  { key: "integrity", label: "Evidence integrity" },
  { key: "relatedness", label: "Out-of-scope evidence" },
];

export function ReportsPage() {
  const { evidence, events, insights, openEvidence, people, workspace, activeWorkspaceId } = useApp();
  const [sections, setSections] = useState<Record<SectionKey, boolean>>({
    summary: true,
    findings: true,
    chronology: true,
    people: true,
    evidence: true,
    integrity: true,
    relatedness: true,
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [analysis, setAnalysis] = useState<CaseAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const evidenceKey = useMemo(
    () => `${evidence.map((item) => item.id).sort().join(",")}:${events.length}`,
    [evidence, events.length],
  );

  useEffect(() => {
    let cancelled = false;
    setAnalysisLoading(true);
    void api
      .caseAnalysis()
      .then((result) => {
        if (!cancelled) setAnalysis(result);
      })
      .catch(() => {
        if (!cancelled) setAnalysis(null);
      })
      .finally(() => {
        if (!cancelled) setAnalysisLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId, evidenceKey]);

  const chronology = useMemo(() => [...events].sort((a, b) => +new Date(a.at) - +new Date(b.at)), [events]);
  const involved = useMemo(
    () => people.filter((p) => evidence.some((e) => e.personIds.includes(p.id))),
    [evidence, people],
  );
  const inconsistencies = insights.filter((i) => i.kind === "anomaly" || i.kind === "link");

  const preview = useMemo(() => {
    const total = evidence.length;
    const verified = evidence.filter((e) => e.integrity === "verified").length;
    const failed = evidence.filter((e) => e.integrity === "mismatch").length;
    return {
      title: "Incident disclosure report",
      caseId: workspace.caseId,
      preparedFor: workspace.name,
      preparedBy: workspace.analyst,
      generatedAt: new Date().toISOString(),
      summary: [
        `${total} evidence item(s) preserved, covering ${people.length} identified people and ${events.length} timeline events.`,
        `${verified} of ${total} item(s) verified against their SHA-256 custody digest.`,
        inconsistencies.length
          ? `${inconsistencies.length} analytical finding(s) recorded for review.`
          : "No analytical findings have been recorded yet.",
      ],
      integrity: { verified, total, failed, algorithm: "SHA-256", ledger: "chained custody ledger" },
    };
  }, [evidence, events.length, inconsistencies.length, people.length, workspace]);

  const disclosureChecks = useMemo(
    () => [
      {
        label: "Evidence preserved",
        detail: `${evidence.length} item(s)`,
        ok: evidence.length > 0,
      },
      {
        label: "Integrity verified",
        detail: `${preview.integrity.verified}/${preview.integrity.total} verified`,
        ok:
          preview.integrity.total > 0 &&
          preview.integrity.failed === 0 &&
          preview.integrity.verified === preview.integrity.total,
      },
      {
        label: "Supporting evidence section",
        detail: sections.evidence ? "Included" : "Enable it in document settings",
        ok: sections.evidence,
      },
      {
        label: "Integrity section",
        detail: sections.integrity ? "Included" : "Enable it in document settings",
        ok: sections.integrity,
      },
      {
        label: "Chronology section",
        detail: sections.chronology ? "Included" : "Enable it in document settings",
        ok: sections.chronology,
      },
      {
        label: "Case type identified",
        detail: analysis?.caseTypes?.length
          ? analysis.caseTypes.map((type) => type.label).join(", ")
          : analysisLoading
            ? "Analysing…"
            : "Not classified",
        ok: (analysis?.caseTypes?.length ?? 0) > 0,
      },
      {
        label: "People resolved",
        detail: `${people.length} resolved`,
        ok: people.length > 0,
      },
    ],
    [analysis, analysisLoading, evidence.length, people.length, preview.integrity, sections],
  );
  const passedChecks = disclosureChecks.filter((check) => check.ok).length;
  const disclosureReady = passedChecks === disclosureChecks.length;

  // Print-to-PDF so the download follows the selected document sections.
  const downloadPdf = () => {
    window.print();
  };

  return (
    <div className="animate-fade-in">
      <div className="print-hidden">
        <PageHeader
          eyebrow={
            <>
              <Badge tone="neutral">{workspace.caseId}</Badge>
              <Badge tone={disclosureReady ? "success" : "warning"} dot>
                {disclosureReady ? "Ready for disclosure" : "Needs review"}
              </Badge>
            </>
          }
          title="Reports"
          description="Assemble a court-ready narrative from preserved evidence. Every claim keeps its source and its hash."
          actions={
            <>
              <Button variant="secondary" onClick={() => setSettingsOpen(true)}>
                <SlidersHorizontal className="h-3.5 w-3.5" /> Document settings
              </Button>
              <Button variant="primary" onClick={downloadPdf}>
                <Download className="h-3.5 w-3.5" /> Download PDF
              </Button>
            </>
          }
        />
      </div>

      <div className="print-hidden mb-3 rounded-card border border-line bg-surface p-3 shadow-card">
        <div className="flex flex-wrap items-center gap-2">
          <ShieldCheck
            className={cn("h-3.5 w-3.5", disclosureReady ? "text-success" : "text-warning")}
          />
          <h2 className="text-[12.5px] font-semibold">Disclosure check</h2>
          <Badge tone={disclosureReady ? "success" : "warning"} dot>
            {disclosureReady ? "Ready for disclosure" : "Needs review"}
          </Badge>
          <span className="ml-auto text-[10.5px] text-ink-3">
            {passedChecks}/{disclosureChecks.length} checks passed
          </span>
        </div>
        <ul className="mt-2 grid gap-x-4 gap-y-1.5 sm:grid-cols-2 lg:grid-cols-3">
          {disclosureChecks.map((check) => (
            <li key={check.label} className="flex items-start gap-1.5 text-[11px]">
              {check.ok ? (
                <Check className="mt-px h-3 w-3 shrink-0 text-success" />
              ) : (
                <CircleAlert className="mt-px h-3 w-3 shrink-0 text-warning" />
              )}
              <span className="text-ink-2">{check.label}</span>
              <span className="truncate text-ink-3">· {check.detail}</span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <article
          id="report-preview"
          className="print-area overflow-hidden rounded-card border border-line bg-surface shadow-card print:border-0 print:shadow-none"
        >
          <div className="border-b border-line bg-surface-2/60 px-6 py-3 print:hidden">
            <div className="flex flex-wrap items-center gap-2">
              <FileCheck2 className="h-3.5 w-3.5 text-ink-3" />
              <span className="text-[11.5px] font-medium">Live preview</span>
              <span className="text-[10.5px] text-ink-3">· {preview.title}</span>
              <Badge tone="success" className="ml-auto">
                Final
              </Badge>
              <Badge tone="neutral">Confidential</Badge>
            </div>
          </div>

          <div className="px-6 py-7 sm:px-10 sm:py-9">
            <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-5">
              <div>
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-ink text-surface">
                    <ShieldCheck className="h-3 w-3" />
                  </span>
                  <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-2">Veritas</span>
                  <span className="text-[10px] text-ink-3">· Kestrel Legal</span>
                </div>
                <h2 className="mt-3 max-w-lg text-[21px] font-semibold leading-tight tracking-[-0.025em] sm:text-[24px]">
                  {preview.title}
                </h2>
                <p className="mt-1.5 text-[11.5px] text-ink-2">
                  Matter {preview.caseId} · Digital evidence intelligence report
                </p>
              </div>
              <div className="text-left text-[10.5px] leading-relaxed text-ink-3 sm:text-right">
                <p>
                  Prepared for <span className="font-medium text-ink-2">{preview.preparedFor}</span>
                </p>
                <p>
                  Prepared by <span className="font-medium text-ink-2">{preview.preparedBy}</span>
                </p>
                <p>Generated {formatDateTime(preview.generatedAt)} IST</p>
              </div>
            </header>

            <div className="mt-6 space-y-7">
              {sections.summary && (
                <section>
                  <SectionTitle index="01" title="Incident summary" />
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] uppercase tracking-wide text-ink-3">Case type</span>
                    {analysis?.caseTypes?.length ? (
                      analysis.caseTypes.map((type) => (
                        <Badge
                          key={type.label}
                          tone="danger"
                          className="h-[19px] text-[10px] capitalize"
                        >
                          {type.label} · {Math.round(type.confidence * 100)}%
                        </Badge>
                      ))
                    ) : (
                      <span className="text-[10.5px] text-ink-3">
                        {analysisLoading ? "Analysing…" : "Not classified"}
                      </span>
                    )}
                    {analysis?.caseTypes?.length ? (
                      <span className="text-[9.5px] text-ink-3">
                        {analysis.mode === "ai" ? "AI-classified" : "Keyword-classified"}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-2.5 space-y-2.5">
                    {(analysis?.summary ? [analysis.summary] : preview.summary).map((p, i) => (
                      <p key={i} className="whitespace-pre-line text-[12.5px] leading-[1.75] text-ink-2">
                        {p}
                      </p>
                    ))}
                    {analysisLoading && !analysis && (
                      <p className="text-[11px] text-ink-3">Generating detailed case summary…</p>
                    )}
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    {[
                      ["Total size", formatBytes(evidence.reduce((sum, item) => sum + item.size, 0))],
                      ["People", `${people.length} identified`],
                      ["Evidence items", `${evidence.length} preserved`],
                    ].map(([k, v]) => (
                      <div key={k} className="rounded-lg border border-line bg-surface-2 px-3 py-2">
                        <p className="text-[9.5px] uppercase tracking-wide text-ink-3">{k}</p>
                        <p className="mt-0.5 text-[12.5px] font-semibold tabular-nums">{v}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {sections.findings && (
                <section>
                  <SectionTitle index="02" title="Key findings & inconsistencies" />
                  <ul className="mt-2.5 space-y-2">
                    {inconsistencies.map((finding) => (
                      <li key={finding.id} className="flex gap-2.5 rounded-lg border border-line px-3 py-2.5">
                        <span
                          className={cn(
                            "mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full",
                            finding.severity === "critical" ? "bg-danger" : "bg-warning",
                          )}
                        />
                        <div className="min-w-0 flex-1">
                          <p className="flex flex-wrap items-center gap-2 text-[12px] font-medium">
                            {finding.title}
                            <span className="text-[10px] font-normal text-ink-3">
                              {finding.confidence}% confidence
                            </span>
                          </p>
                          <p className="mt-0.5 text-[11.5px] leading-relaxed text-ink-2">{finding.body}</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {finding.evidenceIds.map((id) => {
                              const item = evidence.find((e) => e.id === id);
                              if (!item) return null;
                              return (
                                <button
                                  key={id}
                                  onClick={() => openEvidence(id)}
                                  className="print-hidden text-[9.5px] text-accent hover:underline"
                                >
                                  {item.name}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {sections.chronology && (
                <section>
                  <SectionTitle index="03" title="Chronological events" />
                  <div className="mt-2.5 overflow-hidden rounded-lg border border-line">
                    <table className="w-full border-collapse text-left">
                      <thead>
                        <tr className="bg-surface-2 text-[9.5px] uppercase tracking-wide text-ink-3">
                          <th className="px-3 py-1.5 font-medium">Date / time</th>
                          <th className="px-3 py-1.5 font-medium">Event</th>
                          <th className="hidden px-3 py-1.5 font-medium sm:table-cell">Category</th>
                          <th className="hidden px-3 py-1.5 font-medium md:table-cell">People</th>
                        </tr>
                      </thead>
                      <tbody>
                        {chronology.map((event) => (
                          <tr key={event.id} className="border-t border-line align-top">
                            <td className="whitespace-nowrap px-3 py-1.5 text-[10.5px] tabular-nums text-ink-3">
                              {formatDate(event.at)}
                              <span className="ml-1 text-ink-2">{formatTime(event.at)}</span>
                            </td>
                            <td className="px-3 py-1.5 text-[10.5px] font-medium">
                              {event.title}
                              {event.severity === "critical" && (
                                <span className="ml-1.5 rounded bg-danger/10 px-1 text-[8.5px] font-medium uppercase text-danger">
                                  critical
                                </span>
                              )}
                            </td>
                            <td className="hidden px-3 py-1.5 text-[10px] text-ink-2 sm:table-cell">{event.category}</td>
                            <td className="hidden max-w-[150px] truncate px-3 py-1.5 text-[10px] text-ink-2 md:table-cell">
                              {people
                                .filter((p) => event.personIds.includes(p.id))
                                .map((p) => p.name)
                                .join(", ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="mt-1.5 text-[9.5px] text-ink-3">
                    Times shown in IST. Source references are retained in the accompanying evidence register.
                  </p>
                </section>
              )}

              {sections.people && (
                <section>
                  <SectionTitle index="04" title="People involved" />
                  <div className="mt-2.5 overflow-hidden rounded-lg border border-line">
                    <table className="w-full border-collapse text-left">
                      <thead>
                        <tr className="bg-surface-2 text-[9.5px] uppercase tracking-wide text-ink-3">
                          <th className="px-3 py-1.5 font-medium">Name</th>
                          <th className="px-3 py-1.5 font-medium">Role</th>
                          <th className="hidden px-3 py-1.5 font-medium sm:table-cell">Contact</th>
                          <th className="px-3 py-1.5 font-medium text-right">Files</th>
                        </tr>
                      </thead>
                      <tbody>
                        {involved.map((person) => (
                          <tr key={person.id} className="border-t border-line">
                            <td className="px-3 py-1.5 text-[10.5px] font-medium">{person.name}</td>
                            <td className="px-3 py-1.5 text-[10px] text-ink-2">
                              {person.role}
                              {person.risk === "high" && (
                                <span className="ml-1.5 inline-block h-1 w-1 rounded-full bg-danger align-middle" />
                              )}
                            </td>
                            <td className="hidden px-3 py-1.5 text-[10px] text-ink-2 sm:table-cell">
                              {person.phone ?? person.email}
                            </td>
                            <td className="px-3 py-1.5 text-right text-[10px] tabular-nums text-ink-2">
                              {person.evidenceCount}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}

              {sections.evidence && (
                <section>
                  <SectionTitle index="05" title="Supporting evidence register" />
                  <div className="mt-2.5 overflow-hidden rounded-lg border border-line">
                    <table className="w-full border-collapse text-left">
                      <thead>
                        <tr className="bg-surface-2 text-[9.5px] uppercase tracking-wide text-ink-3">
                          <th className="px-3 py-1.5 font-medium">Reference</th>
                          <th className="hidden px-3 py-1.5 font-medium sm:table-cell">Type</th>
                          <th className="px-3 py-1.5 font-medium">SHA-256</th>
                          <th className="px-3 py-1.5 text-right font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {evidence.slice(0, 10).map((item) => (
                          <tr key={item.id} className="border-t border-line">
                            <td className="max-w-[220px] truncate px-3 py-1.5 text-[10px] font-medium">{item.name}</td>
                            <td className="hidden px-3 py-1.5 text-[10px] uppercase text-ink-3 sm:table-cell">
                              {item.type}
                            </td>
                            <td className="px-3 py-1.5 font-mono text-[9.5px] text-ink-2">
                              {truncateHash(item.hash, 12, 6)}
                            </td>
                            <td className="px-3 py-1.5 text-right">
                              <span
                                className={cn(
                                  "text-[9.5px] font-medium",
                                  item.integrity === "verified"
                                    ? "text-success"
                                    : item.integrity === "pending"
                                      ? "text-warning"
                                      : "text-danger",
                                )}
                              >
                                {item.integrity === "verified" ? "Verified" : item.integrity === "pending" ? "Pending" : "Mismatch"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="mt-1.5 text-[9.5px] text-ink-3">
                    Full register with 14 entries and custody timestamps supplied separately.
                  </p>
                </section>
              )}

              {sections.integrity && (
                <section>
                  <SectionTitle index="06" title="Evidence integrity" />
                  <div className="mt-2.5 rounded-lg border border-line p-3.5">
                    <div className="flex flex-wrap items-start gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-success/10 text-success">
                        <Fingerprint className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-[11.5px] font-medium">
                          {preview.integrity.verified} of {preview.integrity.total} items verified
                          <span className="ml-2 font-normal text-danger">
                            {preview.integrity.failed} mismatch excluded
                          </span>
                        </p>
                        <p className="mt-1 text-[10.5px] leading-relaxed text-ink-2">
                          All items were hashed with {preview.integrity.algorithm} at intake and re-verified
                          after processing.
                          {preview.integrity.failed > 0
                            ? ` ${preview.integrity.failed} item(s) failed verification and are excluded from findings.`
                            : " No integrity mismatches were detected."}
                        </p>
                        <p className="mt-1.5 font-mono text-[9.5px] text-ink-3">
                          {preview.integrity.ledger}
                        </p>
                      </div>
                    </div>
                  </div>
                </section>
              )}

              {sections.relatedness && (
                <section>
                  <SectionTitle index="07" title="Out-of-scope / unrelated evidence" />
                  {analysis?.unrelated && analysis.unrelated.length > 0 ? (
                    <ul className="mt-2.5 space-y-1.5">
                      {analysis.unrelated.map((item, index) => (
                        <li
                          key={`${item.name}-${index}`}
                          className="rounded-lg border border-warning/25 bg-warning/10 px-3 py-2"
                        >
                          <p className="flex items-center gap-1.5 text-[11.5px] font-medium">
                            <CircleAlert className="h-3 w-3 text-warning" /> {item.name}
                          </p>
                          <p className="mt-0.5 text-[10.5px] leading-relaxed text-ink-2">{item.reason}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-[11.5px] leading-relaxed text-ink-2">
                      {analysisLoading
                        ? "Checking evidence relatedness…"
                        : "No out-of-scope evidence was identified."}
                    </p>
                  )}
                  {analysis?.limitations?.[0] && (
                    <p className="mt-2 text-[10px] text-ink-3">{analysis.limitations[0]}</p>
                  )}
                </section>
              )}
            </div>

            <footer className="mt-8 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3 text-[9px] text-ink-3">
              <span>Confidential · Prepared for legal proceedings · {preview.caseId}</span>
              <span className="font-mono">Generated {formatDateTime(preview.generatedAt)}</span>
            </footer>
          </div>
        </article>
      </div>

      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-w-md p-5">
          <DialogTitle className="text-[15px] font-semibold">Document settings</DialogTitle>
          <DialogDescription className="mt-1 text-[12px] leading-relaxed text-ink-2">
            Choose which sections appear in the live preview and in the downloaded PDF.
          </DialogDescription>

          <div className="mt-4 space-y-2.5">
            {sectionLabels.map((section) => (
              <div key={section.key} className="flex items-center justify-between gap-2">
                <span className="text-[12px] text-ink-2">{section.label}</span>
                <Switch
                  checked={sections[section.key]}
                  onChange={(next) => setSections((prev) => ({ ...prev, [section.key]: next }))}
                  label={section.label}
                />
              </div>
            ))}
          </div>

          <p className="mt-3 rounded-lg bg-surface-2 p-2.5 text-[10.5px] leading-relaxed text-ink-3">
            {Object.values(sections).filter(Boolean).length} of {sectionLabels.length} sections enabled. The
            downloaded PDF includes only the enabled sections.
          </p>

          <div className="mt-4 flex justify-end">
            <Button variant="primary" size="sm" onClick={() => setSettingsOpen(false)}>
              Done
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SectionTitle({ index, title }: { index: string; title: string }) {
  return (
    <div className="flex items-baseline gap-2 border-b border-line pb-1.5">
      <span className="font-mono text-[9.5px] text-ink-3">{index}</span>
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-2">{title}</h3>
    </div>
  );
}
