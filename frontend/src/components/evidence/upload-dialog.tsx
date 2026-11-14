import { useState } from "react";
import type { EvidenceType, Person } from "@/data/types";
import type { UploadMeta } from "@/lib/api";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { FileTypeTile } from "./file-type";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

function typeOf(file: File): EvidenceType {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("audio/")) return "audio";
  if (file.type === "application/pdf") return "document";
  if (/(chat|whatsapp|telegram|export|messages?)/i.test(file.name)) return "chat";
  return "data";
}

interface UploadDialogProps {
  files: File[] | null;
  people: Person[];
  onClose: () => void;
  onSubmit: (meta: UploadMeta) => void;
}

export function UploadDialog({ files, people, onClose, onSubmit }: UploadDialogProps) {
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [location, setLocation] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [extra, setExtra] = useState("");
  const [note, setNote] = useState("");
  const [autoDetect, setAutoDetect] = useState(true);

  const togglePerson = (name: string) => {
    setSelected((prev) => (prev.includes(name) ? prev.filter((item) => item !== name) : [...prev, name]));
  };

  const submit = () => {
    const extras = extra
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    onSubmit({
      date: date || undefined,
      time: time || undefined,
      location: location.trim() || undefined,
      persons: Array.from(new Set([...selected, ...extras])),
      note: note.trim() || undefined,
      autoDetect,
    });
  };

  const count = files?.length ?? 0;

  return (
    <Dialog open={files !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg p-5">
        <DialogTitle className="text-[15px] font-semibold">Add evidence details</DialogTitle>
        <DialogDescription className="mt-1 text-[12px] leading-relaxed text-ink-2">
          Record when and where this item was captured. These details are stored with the preserved file.
        </DialogDescription>

        {files && files.length > 0 && (
          <div className="mt-3 max-h-28 space-y-1 overflow-y-auto rounded-lg border border-line bg-surface-2 p-2">
            {files.map((file) => (
              <div key={file.name} className="flex items-center gap-2 text-[11.5px]">
                <FileTypeTile type={typeOf(file)} size="sm" />
                <span className="min-w-0 flex-1 truncate">{file.name}</span>
                <span className="shrink-0 text-ink-3">{formatBytes(file.size)}</span>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Field label="Date" hint="Leave blank to auto-detect from the file.">
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
          <Field label="Time" hint="Leave blank to auto-detect from the file.">
            <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
          </Field>
        </div>

        <div className="mt-3">
          <Field label="Location" hint="Leave blank to auto-detect from the file.">
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Hotel Sunrise, Pune"
            />
          </Field>
        </div>

        <div className="mt-3">
          <p className="mb-1.5 text-[12.5px] font-medium text-ink-2">People involved</p>
          <div className="flex flex-wrap gap-1.5">
            {people.map((person) => {
              const active = selected.includes(person.name);
              return (
                <button
                  key={person.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => togglePerson(person.name)}
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-[11.5px] font-medium transition-colors",
                    active
                      ? "border-accent bg-accent-soft text-accent"
                      : "border-line bg-surface text-ink-2 hover:bg-surface-2",
                  )}
                >
                  {person.name}
                </button>
              );
            })}
          </div>
          <Input
            className="mt-2"
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder="Other people (comma separated)"
          />
        </div>

        <div className="mt-3">
          <Field label="Note" hint="Optional description saved with the item.">
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="w-full resize-none rounded-[10px] border border-line bg-surface px-3 py-2 text-[13px] text-ink placeholder:text-ink-3 transition-colors focus:border-accent/60 focus:outline-none"
              placeholder="e.g. Received from the complainant on WhatsApp."
            />
          </Field>
        </div>

        <label className="mt-3 flex items-start gap-2 rounded-lg border border-line bg-surface-2 p-2.5 text-[12px] leading-relaxed text-ink-2">
          <input
            type="checkbox"
            checked={autoDetect}
            onChange={(e) => setAutoDetect(e.target.checked)}
            className="mt-0.5 h-3.5 w-3.5 shrink-0"
          />
          <span>
            Auto-detect missing details from the file
            <span className="block text-[11px] text-ink-3">
              Date, time, location and people are read from the file after processing. Anything you enter
              above is kept as-is.
            </span>
          </span>
        </label>

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={submit}>
            Preserve {count} file{count === 1 ? "" : "s"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
