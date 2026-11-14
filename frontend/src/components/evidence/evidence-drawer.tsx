import {
  ArrowRight,
  Check,
  CheckCheck,
  Copy,
  Download,
  FilePlus2,
  Fingerprint,
  Flag,
  Link2,
  Pencil,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { useApp } from "@/store/app-store";
import { api, isBackendEvidenceId } from "@/lib/api";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { CaptureDialog } from "@/components/evidence/upload-dialog";
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
    deleteEvidence,
    updateCapture,
    markReviewed,
  } = useApp();
  const [copied, setCopied] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [editing, setEditing] = useState(false);
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

  const remove = async () => {
    setDeleting(true);
    await deleteEvidence(item.id);
    setDeleting(false);
    setConfirmDelete(false);
  };

  const download = async () => {
    if (isBackendEvidenceId(item.id)) {
      setDownloading(true);
      try {
        await api.downloadEvidence(item.id, item.name);
        toast("Download ready", `${item.name} · custody stamp included.`, "success");
      } catch (error) {
        toast(
          "Download failed",
          error instanceof Error ? error.message : "The file could not be downloaded.",
          "danger",
        );
      } finally {
        setDownloading(false);
      }
      return;
    }
    if (item.url) {
      const anchor = document.createElement("a");
      anchor.href = item.url;
      anchor.download = item.name;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      return;
    }
    toast("No preserved file", "This demo item has no file stored on the server.", "danger");
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

          {item.needsReview && (
            <div className="rounded-xl border border-warning/30 bg-warning/10 p-3">
              <p className="text-[11.5px] font-medium">Capture details need review</p>
              <p className="mt-1 text-[11px] leading-relaxed text-ink-2">
                Missing: {item.missingCapture?.join(", ") || "capture details"}. Add them with
                <span className="font-medium text-ink"> Edit details</span>, or skip this check.
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-2"
                onClick={() => void markReviewed(item.id)}
              >
                <CheckCheck className="h-3.5 w-3.5" /> Mark as reviewed
              </Button>
            </div>
          )}

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
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-[11px] font-medium uppercase tracking-[0.05em] text-ink-3">
                Metadata
              </h4>
              <button
                onClick={() => setEditing(true)}
                className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10.5px] font-medium text-ink-3 transition-colors hover:bg-surface-3 hover:text-ink"
              >
                <Pencil className="h-3 w-3" /> Edit details
              </button>
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5 rounded-xl border border-line p-3.5">
              <Meta label="File type" value={`${meta.label} · ${item.mime.split("/")[1] ?? item.mime}`} />
              <Meta label="Size" value={formatBytes(item.size)} />
              <Meta label="Preserved" value={`${formatDate(item.uploadedAt)}, ${formatTime(item.uploadedAt)}`} />
              <Meta label="Custodian" value={item.uploadedBy} />
              <Meta label="Source" value={item.source} className="col-span-2" />
              {item.occurredAt && (
                <Meta
                  label={
                    item.captureDetected?.includes("occurredAt") ? "Captured (auto-detected)" : "Captured"
                  }
                  value={`${formatDate(item.occurredAt)}, ${formatTime(item.occurredAt)}`}
                  className="col-span-2"
                />
              )}
              {item.location && (
                <Meta
                  label={item.captureDetected?.includes("location") ? "Location (auto-detected)" : "Location"}
                  value={item.location}
                />
              )}
              {item.persons && item.persons.length > 0 && (
                <Meta
                  label={item.captureDetected?.includes("persons") ? "People (auto-detected)" : "People"}
                  value={item.persons.join(", ")}
                  className="col-span-2"
                />
              )}
              {item.captureNote && (
                <Meta label="Capture note" value={item.captureNote} className="col-span-2" />
              )}
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
            onClick={download}
            disabled={downloading}
          >
            <Download className="h-3.5 w-3.5" /> {downloading ? "Downloading…" : "Download"}
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
          <Button
            variant="ghost"
            size="icon"
            aria-label="Remove from vault"
            title="Remove from vault"
            onClick={() => setConfirmDelete(true)}
            className="text-ink-3 hover:bg-danger/10 hover:text-danger"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </SheetContent>

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent className="max-w-md p-5">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-danger/10 text-danger">
              <Trash2 className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <DialogTitle className="text-[14px] font-semibold">Remove evidence from vault?</DialogTitle>
              <DialogDescription className="mt-1 text-[12px] leading-relaxed text-ink-2">
                <span className="font-medium text-ink">{item.name}</span> will be removed from the active
                vault and its derived index. The original file and SHA-256 custody record are retained.
              </DialogDescription>
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setConfirmDelete(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" onClick={remove} disabled={deleting}>
              <Trash2 className="h-3.5 w-3.5" /> {deleting ? "Removing…" : "Remove"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {editing && (
        <CaptureDialog
          open
          mode="edit"
          people={people}
          initial={{
            date: item.occurredAt ? item.occurredAt.slice(0, 10) : "",
            time: item.occurredAt && item.occurredAt.length >= 16 ? item.occurredAt.slice(11, 16) : "",
            location: item.location ?? "",
            persons: item.persons ?? [],
            note: item.captureNote ?? "",
          }}
          onClose={() => setEditing(false)}
          onSubmit={async (meta) => {
            setEditing(false);
            await updateCapture(item.id, meta);
          }}
        />
      )}
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
