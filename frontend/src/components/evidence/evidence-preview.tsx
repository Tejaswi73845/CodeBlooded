import { Camera, Play, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { EvidenceItem } from "@/data/types";
import { formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";
import { FileTypeTile, typeMeta } from "./file-type";

function Chrome({ label, children, dark }: { label: string; children: React.ReactNode; dark?: boolean }) {
  return (
    <div className={cn("overflow-hidden rounded-xl border border-line", dark ? "bg-[#0d0d0f]" : "bg-surface-2")}>
      <div
        className={cn(
          "flex items-center justify-between border-b px-3 py-1.5 text-[10px] font-medium",
          dark ? "border-white/8 text-white/45" : "border-line text-ink-3",
        )}
      >
        <span>{label}</span>
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-success" /> Preserved copy
        </span>
      </div>
      {children}
    </div>
  );
}

function ThreatScreenshot() {
  return (
    <Chrome label="Screen capture · 10 Nov 22:14" dark>
      <div className="flex flex-col gap-2 p-3">
        <div className="flex items-center gap-2 border-b border-white/8 pb-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-[9px] text-white/70">
            ?
          </div>
          <div>
            <p className="text-[10.5px] font-medium text-white/80">+91 90040 51279</p>
            <p className="text-[9px] text-white/35">Unknown sender</p>
          </div>
        </div>
        <div className="ml-auto max-w-[80%] rounded-[10px] rounded-br-[3px] bg-[#0A84FF] px-2.5 py-1.5 text-[10.5px] leading-snug text-white">
          Transfer the revised amount before 9am. The board already has the old invoices.
        </div>
        <div className="max-w-[70%] rounded-[10px] rounded-bl-[3px] bg-white/8 px-2.5 py-1.5 text-[10.5px] leading-snug text-white/80">
          Who is this?
        </div>
        <div className="ml-auto max-w-[80%] rounded-[10px] rounded-br-[3px] bg-[#0A84FF] px-2.5 py-1.5 text-[10.5px] leading-snug text-white">
          You know exactly who this is. 23:40, don't be late.
        </div>
        <p className="mt-1 text-center text-[9px] text-white/30">22:14 · captured from device</p>
      </div>
    </Chrome>
  );
}

function PaymentScreenshot() {
  return (
    <Chrome label="Screen capture · payment receipt">
      <div className="flex flex-col items-center gap-1.5 px-4 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-success/12 text-success">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M4 12.5 9 17.5 20 6.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <p className="text-[11px] font-medium">Payment successful</p>
        <p className="text-[20px] font-semibold tracking-tight">₹18,50,000</p>
        <p className="text-[10px] text-ink-3">Rao Enterprises · HDFC ••4471</p>
        <div className="mt-1.5 w-full space-y-1 rounded-lg bg-surface p-2 text-[9.5px]">
          <div className="flex justify-between">
            <span className="text-ink-3">UTR</span>
            <span className="font-mono">HDFC22611X8842</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-3">Date</span>
            <span>11 Nov 2026, 08:05</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-3">Mode</span>
            <span>RTGS · two tranches</span>
          </div>
        </div>
      </div>
    </Chrome>
  );
}

function InstagramDM() {
  return (
    <Chrome label="Screen capture · Instagram direct">
      <div className="space-y-2 p-3">
        <div className="flex items-center gap-2 border-b border-line pb-2">
          <div className="h-6 w-6 rounded-full bg-gradient-to-br from-[#AF52DE] to-[#FF9F0A]" />
          <div>
            <p className="text-[10.5px] font-medium">@neha.v_88</p>
            <p className="text-[9px] text-ink-3">Active 2h ago</p>
          </div>
        </div>
        <div className="max-w-[85%] rounded-[10px] rounded-bl-[3px] bg-surface px-2.5 py-1.5 text-[10.5px] leading-snug">
          Did you swap the handset before the verification call?
        </div>
        <div className="ml-auto max-w-[80%] rounded-[10px] rounded-br-[3px] bg-accent px-2.5 py-1.5 text-[10.5px] leading-snug text-white">
          Yes. Old one is off. Use the new number from now on.
        </div>
        <p className="pt-1 text-center text-[9px] text-ink-3">12 Nov 15:44</p>
      </div>
    </Chrome>
  );
}

function ChatPreview() {
  return (
    <Chrome label="Chat transcript · 1,284 messages">
      <div className="space-y-2 p-3">
        {[
          { me: false, text: "Good afternoon. Sharing updated banking details for the annual contract.", time: "14:30" },
          { me: true, text: "Please send this on the official letterhead.", time: "14:36" },
          { me: false, text: "Attached. Kindly process before Friday to avoid dispatch delay.", time: "14:41" },
          { me: true, text: "Received. I will check with accounts.", time: "15:02" },
        ].map((m, i) => (
          <div key={i} className={cn("flex", m.me ? "justify-end" : "justify-start")}>
            <div
              className={cn(
                "max-w-[82%] rounded-[9px] px-2.5 py-1.5 text-[10.5px] leading-snug",
                m.me ? "bg-accent text-white" : "bg-surface",
              )}
            >
              {m.text}
              <span className={cn("ml-2 text-[8.5px]", m.me ? "text-white/60" : "text-ink-3")}>{m.time}</span>
            </div>
          </div>
        ))}
        <p className="pt-1 text-center text-[9px] text-ink-3">Exported from WhatsApp · 1,284 messages</p>
      </div>
    </Chrome>
  );
}

function VideoPreview({ item }: { item: EvidenceItem }) {
  const [playing, setPlaying] = useState(false);
  return (
    <Chrome label={`CCTV · ${item.source.split("·")[1]?.trim() ?? "cam 04"}`} dark>
      <div className="relative flex aspect-[16/9] items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_30%_20%,#2b2f36,transparent_60%),linear-gradient(160deg,#14171c,#08090b)]">
        <div className="absolute inset-x-0 top-2 flex justify-between px-2.5 font-mono text-[9px] text-white/40">
          <span>CAM 04 · EAST CORRIDOR</span>
          <span>10-11-2026 22:38:04</span>
        </div>
        <div className="absolute bottom-2 left-2.5 font-mono text-[9px] text-white/35">
          {formatDuration(item.duration ?? 0)} · H.264
        </div>
        <button
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? "Pause preview" : "Play preview"}
          className="flex h-11 w-11 items-center justify-center rounded-full border border-white/15 bg-white/10 text-white/90 backdrop-blur-sm transition-transform hover:scale-105"
        >
          {playing ? (
            <span className="flex gap-0.5">
              <span className="h-3.5 w-[2px] bg-white/90" />
              <span className="h-3.5 w-[2px] bg-white/90" />
            </span>
          ) : (
            <Play className="ml-0.5 h-4 w-4" fill="currentColor" />
          )}
        </button>
        <div className="absolute inset-x-0 bottom-6 mx-2.5 h-[2px] overflow-hidden rounded bg-white/15">
          <div
            className={cn("h-full bg-accent transition-[width] duration-[8000ms] ease-linear", playing ? "w-2/3" : "w-0")}
          />
        </div>
        <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_3px,rgba(0,0,0,0.18)_3px,rgba(0,0,0,0.18)_4px)] opacity-40" />
      </div>
    </Chrome>
  );
}

function AudioPreview({ item }: { item: EvidenceItem }) {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) return;
    const started = performance.now();
    const loop = (now: number) => {
      setProgress((p) => (p >= 100 ? 0 : p + (now - started) * 0.00004));
      raf.current = requestAnimationFrame(loop);
    };
    raf.current = requestAnimationFrame(loop);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [playing]);

  const bars = Array.from({ length: 52 }, (_, i) => {
    const seed = item.id.charCodeAt(2) + i * 7;
    return 18 + Math.abs(Math.sin(seed * 1.7)) * 52;
  });

  return (
    <Chrome label="Audio · speaker diarised">
      <div className="px-3 pb-3 pt-4">
        <div className="mb-3 flex items-end gap-[3px]">
          {bars.map((h, i) => (
            <span
              key={i}
              className={cn(
                "flex-1 rounded-full transition-colors",
                i < (progress / 100) * bars.length ? "bg-accent" : "bg-line-strong",
              )}
              style={{ height: `${h}px` }}
            />
          ))}
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setPlaying((p) => !p)}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-white"
            aria-label={playing ? "Pause audio preview" : "Play audio preview"}
          >
            {playing ? (
              <span className="flex gap-[2px]">
                <span className="h-3 w-[2px] bg-white" />
                <span className="h-3 w-[2px] bg-white" />
              </span>
            ) : (
              <Play className="ml-0.5 h-3.5 w-3.5" fill="currentColor" />
            )}
          </button>
          <div className="flex-1">
            <p className="truncate text-[10.5px] font-medium">{item.name}</p>
            <p className="text-[9.5px] text-ink-3">
              {formatDuration(((item.duration ?? 0) * progress) / 100)} / {formatDuration(item.duration ?? 0)} · 3 speakers
            </p>
          </div>
        </div>
      </div>
    </Chrome>
  );
}

function DocumentPreview({ item }: { item: EvidenceItem }) {
  return (
    <Chrome label={`PDF · ${item.pages ?? 1} pages`}>
      <div className="p-3">
        <div className="mx-auto max-w-[230px] rounded-sm bg-white p-3 shadow-[0_1px_4px_rgba(0,0,0,0.08)] dark:bg-[#e9e9ec]">
          <p className="mb-2 text-[7.5px] font-semibold uppercase tracking-wide text-gray-500">
            {item.id === "ev-05" ? "HDFC Bank · Statement" : "Meridian Textiles"}
          </p>
          <p className="text-[9.5px] font-semibold leading-tight text-gray-900">
            {item.name.replace(/_/g, " ").replace(/\.(pdf|txt)$/i, "")}
          </p>
          <div className="mt-2 space-y-[3px]">
            {[98, 92, 88, 96, 70, 94, 90, 84, 92, 60].map((w, i) => (
              <div key={i} className="h-[3px] rounded-full bg-gray-300" style={{ width: `${w}%` }} />
            ))}
          </div>
          <div className="mt-2 flex justify-between text-[6.5px] text-gray-400">
            <span>Page 1 of {item.pages ?? 1}</span>
            <span>OCR 99.1%</span>
          </div>
        </div>
      </div>
    </Chrome>
  );
}

function PhotoPreview({ item }: { item: EvidenceItem }) {
  if (item.url) {
    return <img src={item.url} alt={item.name} className="max-h-[300px] w-full rounded-xl border border-line object-contain bg-black/5" />;
  }
  return (
    <Chrome label="Field photograph · EXIF retained">
      <div className="relative aspect-[16/10] overflow-hidden bg-[linear-gradient(175deg,#5b6470_0%,#8d8578_42%,#3c3a38_68%,#1c1c1e_100%)]">
        <div className="absolute left-[12%] top-[26%] h-[26%] w-[46%] rounded-[18px] bg-[#141518]/85 blur-[0.3px]" />
        <div className="absolute left-[18%] top-[34%] h-[18%] w-[34%] rounded-[10px] bg-[#2c3038]/80" />
        <div className="absolute bottom-[18%] left-[10%] h-[10%] w-[80%] bg-[#17181a]/40 blur-md" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_30%,rgba(255,214,160,0.2),transparent_55%)]" />
        <div className="absolute bottom-2 left-2.5 font-mono text-[9px] text-white/55">
          19.0728° N, 72.8826° E · 11-11-2026 17:20
        </div>
        <div className="absolute bottom-2 right-2.5 flex items-center gap-1 rounded bg-black/35 px-1.5 py-0.5 font-mono text-[8.5px] text-white/60">
          <Camera className="h-2.5 w-2.5" /> 4032 × 3024
        </div>
      </div>
    </Chrome>
  );
}

function DataPreview({ item }: { item: EvidenceItem }) {
  const failure = item.integrity === "mismatch";
  return (
    <Chrome label={item.type === "data" ? "Structured data · parsed" : "Data"}>
      <div className="p-3 font-mono text-[9.5px] leading-relaxed">
        {failure && (
          <div className="mb-2 flex items-center gap-1.5 rounded-md bg-danger/10 px-2 py-1.5 text-[9px] text-danger">
            <ShieldAlert className="h-3 w-3" /> Parse stopped at byte 33,690 — export truncated
          </div>
        )}
        <div className="rounded-md bg-surface p-2 text-ink-2">
          <p className="text-ink-3">{"{"}</p>
          <p className="pl-3">"export": "telegram_desktop",</p>
          <p className="pl-3">"messages": [</p>
          <p className="pl-6 text-ink-3">{"{ \"id\": 8842, \"from\": \"Arjun M.\" },"}</p>
          <p className="pl-6 text-ink-3">{"{ \"id\": 8843, \"from\": \"Arjun M.\" },"}</p>
          <p className="pl-6 text-danger">{failure ? "// unexpected end of JSON" : "… 1,284 more"}</p>
          <p className="pl-3">]</p>
          <p className="text-ink-3">{"}"}</p>
        </div>
      </div>
    </Chrome>
  );
}

export function EvidencePreview({ item }: { item: EvidenceItem }) {
  if (item.url && item.type === "image") return <PhotoPreview item={item} />;
  if (item.id.startsWith("local-")) {
    return (
      <Chrome label={`${typeMeta[item.type].label} · preserved original`}>
        <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
          <FileTypeTile type={item.type} size="lg" />
          <p className="mt-2.5 max-w-[260px] truncate text-[11.5px] font-medium">{item.name}</p>
          <p className="mt-1 max-w-[280px] text-[10.5px] leading-relaxed text-ink-3">
            The original is stored byte-for-byte. Inline preview is not generated for this format.
          </p>
          <p className="mt-2 text-[9.5px] text-ink-3">Extraction completes in the processing pipeline</p>
        </div>
      </Chrome>
    );
  }
  if (item.id === "ev-02") return <ThreatScreenshot />;
  if (item.id === "ev-07") return <PaymentScreenshot />;
  if (item.id === "ev-11") return <InstagramDM />;
  if (item.id === "ev-13") return <PhotoPreview item={item} />;
  switch (item.type) {
    case "image":
      return <PhotoPreview item={item} />;
    case "video":
      return <VideoPreview item={item} />;
    case "audio":
      return <AudioPreview item={item} />;
    case "document":
      return <DocumentPreview item={item} />;
    case "chat":
      return <ChatPreview />;
    case "data":
      return <DataPreview item={item} />;
  }
}
