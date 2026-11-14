import { Sparkles } from "lucide-react";
import { useState } from "react";
import type { IncidentEvent } from "@/data/types";
import type { TimelineEventPatch } from "@/lib/api";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";

interface EventEditDialogProps {
  event: IncidentEvent;
  busy: boolean;
  onClose: () => void;
  onSave: (patch: TimelineEventPatch, context: string | undefined, resummarize: boolean) => void;
}

function splitAt(at: string): { date: string; time: string } {
  const date = at.slice(0, 10);
  const rawTime = at.length >= 16 ? at.slice(11, 16) : "";
  return { date, time: rawTime === "00:00" ? "" : rawTime };
}

export function EventEditDialog({ event, busy, onClose, onSave }: EventEditDialogProps) {
  const initial = splitAt(event.at);
  const [title, setTitle] = useState(event.title);
  const [date, setDate] = useState(initial.date);
  const [time, setTime] = useState(initial.time);
  const [location, setLocation] = useState(event.location ?? "");
  const [description, setDescription] = useState(event.description);
  const [context, setContext] = useState("");

  const submit = (resummarize: boolean) => {
    onSave(
      {
        date: date || null,
        time: time || null,
        occurredAtRaw: null,
        title: title.trim() || undefined,
        description: description.trim(),
        location: location.trim() || null,
      },
      context.trim() || undefined,
      resummarize,
    );
  };

  return (
    <Dialog open onOpenChange={(open) => !open && !busy && onClose()}>
      <DialogContent className="max-h-[85dvh] max-w-lg overflow-y-auto p-5">
        <DialogTitle className="text-[15px] font-semibold">Edit timeline event</DialogTitle>
        <DialogDescription className="mt-1 text-[12px] leading-relaxed text-ink-2">
          Correct the date, time or location. You can also tell the AI what actually happened and have it
          rewrite the summary.
        </DialogDescription>

        <div className="mt-4 space-y-3">
          <Field label="Title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} />
          </Field>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Date">
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </Field>
            <Field label="Time" hint="Leave blank if the exact time is unknown.">
              <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
            </Field>
          </div>

          <Field label="Location" hint="Clear to mark the location as not recorded.">
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Office 12, Kalyani Nagar, Pune"
            />
          </Field>

          <Field label="Description" hint="The factual description shown on the card.">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full resize-none rounded-[10px] border border-line bg-surface px-3 py-2 text-[13px] text-ink placeholder:text-ink-3 transition-colors focus:border-accent/60 focus:outline-none"
            />
          </Field>
        </div>

        <div className="mt-4 rounded-lg border border-line bg-surface-2 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-accent">
            <Sparkles className="h-3.5 w-3.5" /> Re-summarise with context
          </div>
          <p className="mt-1 text-[10.5px] leading-relaxed text-ink-3">
            If the AI misread the source, explain the real context. It is treated as authoritative guidance
            for the new summary.
          </p>
          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            rows={3}
            maxLength={2000}
            className="mt-2 w-full resize-none rounded-[10px] border border-line bg-surface px-3 py-2 text-[12.5px] text-ink placeholder:text-ink-3 transition-colors focus:border-accent/60 focus:outline-none"
            placeholder="e.g. This is a customer-support conversation, not a threat. The payment was a refund, not extortion."
          />
        </div>

        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="secondary" size="sm" onClick={() => submit(false)} disabled={busy}>
            Save
          </Button>
          <Button variant="primary" size="sm" onClick={() => submit(true)} disabled={busy}>
            <Sparkles className="h-3.5 w-3.5" /> {busy ? "Working…" : "Save & re-summarise"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
