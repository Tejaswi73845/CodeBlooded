import { FileText } from "lucide-react";
import { useEffect, useState } from "react";
import type { EvidenceItem } from "@/data/types";
import { api, isBackendEvidenceId } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";
import { FileTypeTile, typeMeta } from "./file-type";

function Chrome({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface-2">
      <div className="flex items-center justify-between border-b border-line px-3 py-1.5 text-[10px] font-medium text-ink-3">
        <span>{label}</span>
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-success" /> Preserved copy
        </span>
      </div>
      {children}
    </div>
  );
}

export function EvidencePreview({ item }: { item: EvidenceItem }) {
  const [texts, setTexts] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isBackendEvidenceId(item.id)) return;
    let cancelled = false;
    setLoading(true);
    void api
      .evidenceText(item.id)
      .then((parts) => {
        if (!cancelled) setTexts(parts);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [item.id]);

  if (item.url && item.type === "image") {
    return (
      <img
        src={item.url}
        alt={item.name}
        className="max-h-[300px] w-full rounded-xl border border-line bg-black/5 object-contain"
      />
    );
  }

  return (
    <Chrome label={`${typeMeta[item.type].label} · preserved original`}>
      <div className="p-3">
        <div className="flex items-center gap-2.5">
          <FileTypeTile type={item.type} size="lg" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11.5px] font-medium">{item.name}</p>
            <p className="text-[10px] text-ink-3">
              {typeMeta[item.type].label} · {formatBytes(item.size)}
              {item.pages ? ` · ${item.pages} pages` : ""}
            </p>
          </div>
        </div>
        <div className="mt-2.5 rounded-lg border border-line bg-surface p-2.5">
          <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-medium text-ink-3">
            <FileText className="h-3 w-3" /> Extracted text
          </div>
          {loading ? (
            <p className="text-[10.5px] text-ink-3">Loading…</p>
          ) : texts.length > 0 ? (
            <pre
              className={cn(
                "max-h-40 overflow-y-auto whitespace-pre-wrap break-words font-mono",
                "text-[10px] leading-relaxed text-ink-2",
              )}
            >
              {texts.join("\n\n")}
            </pre>
          ) : (
            <p className="text-[10.5px] leading-relaxed text-ink-3">
              No extracted text is available for this item.
            </p>
          )}
        </div>
      </div>
    </Chrome>
  );
}
