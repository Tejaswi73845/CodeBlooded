import {
  ArrowRight,
  Check,
  Copy,
  Download,
  FilePlus2,
  Fingerprint,
  Flag,
  Link2,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { useApp } from "@/store/app-store";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EvidencePreview } from "./evidence-preview";
import { IntegrityBadge, StatusBadge, typeMeta } from "./file-type";
import { PersonAvatar } from "@/components/person-avatar";
import { formatBytes, formatDate, formatDuration, formatTime } from "@/lib/format";

export function EvidenceDrawer() {
  const {
    openEvidenceId,
    closeEvidence,
    evidence,
    people,
    events,
    navigate,
    selectPerson,
    toast,
  } = useApp();
  const [copied, setCopied] = useState(false);
  const item = evidence.find((e) => e.id === openEvidenceId);

  if (!item) {
    return <Sheet open={false} onOpenChange={() => closeEvidence()} />;
  }

  const linkedPeople = people.filter((p) => item.personIds.includes(p.id));
  const linkedEvents = events.filter((e) => item.eventIds.includes(e.id));
  const meta = typeMeta[item.type];

  const copyHash = async () => {
    await navigator.clipboard.writeText(item.hash);
    setCopied(true);
    toast("Hash copied", "SHA-256 digest copied to clipboard.");
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <Sheet open onOpenChange={(open) => !open && closeEvidence()}>
      <SheetContent
        title={item.name}
        description={`${meta.label} · ${item.source}`}
        className="max-w-[500px]"
      >
        <div className="space-y-5 px-5 py-5">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={item.status} />
            <IntegrityBadge integrity={item.integrity} />
            {item.id.startsWith("local-") && <Badge tone="accent">New intake</Badge>}
            <span className="ml-auto text-[11px] text-ink-3">{formatDate(item.uploadedAt)}</span>
          </div>

          <EvidencePreview item={item} />

          <div className="rounded-xl border border-line bg-surface-2 p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-accent">
              <Sparkles className="h-3.5 w-3.5" /> AI evidence note
            </div>
            <p className="text-[12.5px] leading-relaxed text-ink-2">{item.note}</p>
            <p className="mt-2 text-[10.5px] text-ink-3">
              {item.id.startsWith("local-")
                ? "Generated on intake · awaiting analyst review"
                : "Generated from the preserved copy · confidence 91% · analyst review required"}
            </p>
          </div>

          <section>
            <h4 className="mb-2 text-[11px] font-medium uppercase tracking-[0.05em] text-ink-3">
              Metadata
            </h4>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5 rounded-xl border border-line p-3.5">
              <Meta label="File type" value={`${meta.label} · ${item.mime.split("/")[1] ?? item.mime}`} />
              <Meta label="Size" value={formatBytes(item.size)} />
              <Meta label="Preserved" value={`${formatDate(item.uploadedAt)}, ${formatTime(item.uploadedAt)}`} />
              <Meta label="Custodian" value={item.uploadedBy} />
              <Meta label="Source" value={item.source} className="col-span-2" />
              {item.duration && <Meta label="Duration" value={formatDuration(item.duration)} />}
              {item.pages && <Meta label="Extent" value={`${item.pages} pages`} />}
            </dl>
          </section>

          <section>
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-[11px] font-medium uppercase tracking-[0.05em] text-ink-3">
                Integrity
              </h4>
              <IntegrityBadge integrity={item.integrity} />
            </div>
            <div className="rounded-xl border border-line p-3.5">
              <div className="mb-1.5 flex items-center gap-1.5 text-[11px] text-ink-2">
                <Fingerprint className="h-3.5 w-3.5 text-ink-3" /> SHA-256
              </div>
              <div className="flex items-start gap-2">
                <code className="min-w-0 flex-1 break-all font-mono text-[10.5px] leading-relaxed text-ink-2">
                  {item.hash}
                </code>
                <button
                  onClick={copyHash}
                  aria-label="Copy SHA-256 hash"
                  className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-ink-3 transition-colors hover:bg-surface-3 hover:text-ink"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
              <p className="mt-2 text-[10.5px] leading-relaxed text-ink-3">
                {item.integrity === "verified"
                  ? "Digest re-computed after processing and matched the custody ledger entry."
                  : item.integrity === "pending"
                    ? "Digest recorded at intake. Verification completes after the current pipeline stage."
                    : "Digest does not match the source manifest. Item is excluded from findings."}
              </p>
            </div>
          </section>

          {linkedPeople.length > 0 && (
            <section>
              <h4 className="mb-2 text-[11px] font-medium uppercase tracking-[0.05em] text-ink-3">
                People referenced
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {linkedPeople.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      selectPerson(p.id);
                      closeEvidence();
                      navigate("people");
                    }}
                    className="flex items-center gap-1.5 rounded-full border border-line bg-surface py-1 pl-1 pr-2.5 text-[11.5px] transition-colors hover:bg-surface-2"
                  >
                    <PersonAvatar person={p} size="xs" />
                    {p.name}
                    <ArrowRight className="h-3 w-3 text-ink-3" />
                  </button>
                ))}
              </div>
            </section>
          )}

          {linkedEvents.length > 0 && (
            <section>
              <h4 className="mb-2 text-[11px] font-medium uppercase tracking-[0.05em] text-ink-3">
                Timeline events
              </h4>
              <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line">
                {linkedEvents.map((e) => (
                  <li key={e.id}>
                    <button
                      onClick={() => {
                        closeEvidence();
                        navigate("timeline");
                      }}
                      className="flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors hover:bg-surface-2"
                    >
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                      <span className="min-w-0 flex-1 truncate text-[12px]">{e.title}</span>
                      <span className="shrink-0 text-[10.5px] text-ink-3">
                        {formatDate(e.at)} · {formatTime(e.at)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h4 className="mb-2 text-[11px] font-medium uppercase tracking-[0.05em] text-ink-3">Tags</h4>
            <div className="flex flex-wrap gap-1.5">
              {item.tags.map((tag) => (
                <Badge key={tag} tone="neutral">
                  {tag}
                </Badge>
              ))}
            </div>
          </section>

          <div className="flex items-center gap-1.5 border-t border-line pt-3 text-[10.5px] text-ink-3">
            <Link2 className="h-3 w-3" /> Chain of custody: preserved → hashed → processed → reviewed
          </div>
        </div>

        <div className="sticky bottom-0 flex items-center gap-2 border-t border-line bg-surface/95 px-5 py-3 backdrop-blur-xl">
          <Button
            variant="primary"
            size="md"
            className="flex-1"
            onClick={() => toast("Download prepared", `${item.name} · custody stamp included.`, "success")}
          >
            <Download className="h-3.5 w-3.5" /> Download
          </Button>
          <Button
            variant="secondary"
            size="md"
            onClick={() => toast("Added to report", "Evidence reference appended to the working draft.", "success")}
          >
            <FilePlus2 className="h-3.5 w-3.5" /> Add to report
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Flag for review"
            onClick={() => toast("Flagged for review", "A reviewer has been assigned.", "default")}
          >
            <Flag className="h-4 w-4" />
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Meta({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className={className}>
      <dt className="text-[10.5px] text-ink-3">{label}</dt>
      <dd className="mt-0.5 truncate text-[12px] font-medium text-ink" title={value}>
        {value}
      </dd>
    </div>
  );
}
