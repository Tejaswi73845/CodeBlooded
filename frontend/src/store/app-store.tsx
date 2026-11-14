import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  auditLogs as seedAudit,
  evidence as seedEvidence,
  events,
  insights as seedInsights,
  notifications as seedNotifications,
  people,
  pipeline,
} from "@/data/mock";
import type { EvidenceItem, EvidenceStatus, EvidenceType, Insight } from "@/data/types";
import { api, type UploadMeta } from "@/lib/api";
import { answer, type ChatMessage } from "@/lib/assistant";
import { formatBytes } from "@/lib/format";

export type View =
  | "overview"
  | "vault"
  | "timeline"
  | "people"
  | "assistant"
  | "reports"
  | "audit"
  | "settings";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  tone: "default" | "success" | "danger";
}

interface AppContextValue {
  view: View;
  navigate: (view: View) => void;
  theme: "light" | "dark";
  toggleTheme: () => void;
  evidence: EvidenceItem[];
  people: typeof people;
  events: typeof events;
  pipeline: typeof pipeline;
  insights: Insight[];
  notifications: typeof seedNotifications;
  auditLogs: typeof seedAudit;
  unreadCount: number;
  markRead: (id: string) => void;
  markAllRead: () => void;
  reviewInsight: (id: string) => void;
  openEvidenceId: string | null;
  openEvidence: (id: string) => void;
  closeEvidence: () => void;
  selectedPersonId: string | null;
  selectPerson: (id: string | null) => void;
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  uploads: Record<string, number>;
  uploadFiles: (files: File[], meta?: UploadMeta) => void;
  deleteEvidence: (id: string) => Promise<void>;
  messages: ChatMessage[];
  thinking: boolean;
  ask: (question: string) => void;
  clearChat: () => void;
  toasts: Toast[];
  toast: (title: string, description?: string, tone?: Toast["tone"]) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

function inferType(file: File): EvidenceType {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("audio/")) return "audio";
  if (file.type === "application/pdf") return "document";
  if (/\.(csv|json|xlsx|xls)$/i.test(file.name)) return "data";
  if (/(chat|whatsapp|telegram|export|messages?)/i.test(file.name)) return "chat";
  return "data";
}

const STATUS_MAP: Record<string, EvidenceStatus> = {
  pending: "queued",
  processing: "processing",
  completed: "processed",
  failed: "failed",
};

function mapStatus(value: string): EvidenceStatus {
  return STATUS_MAP[value] ?? "processing";
}

function mapIntegrity(value: string | undefined): EvidenceItem["integrity"] {
  if (value === "verified") return "verified";
  if (value === "mismatch") return "mismatch";
  return "pending";
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [view, setView] = useState<View>("overview");
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem("veritas-theme") as "light" | "dark") || "light",
  );
  const [evidence, setEvidence] = useState<EvidenceItem[]>(seedEvidence);
  const [insights, setInsights] = useState<Insight[]>(seedInsights);
  const [notifications, setNotifications] = useState(seedNotifications);
  const [auditLogs, setAuditLogs] = useState(seedAudit);
  const [openEvidenceId, setOpenEvidenceId] = useState<string | null>(null);
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [uploads, setUploads] = useState<Record<string, number>>({});
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [thinking, setThinking] = useState(false);
  const timers = useRef<number[]>([]);
  const chatGeneration = useRef(0);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
    localStorage.setItem("veritas-theme", theme);
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    void api.listEvidence().then((items) => {
      if (cancelled || items.length === 0) return;
      setEvidence((prev) => {
        const seen = new Set(items.map((item) => item.id));
        return [...items, ...prev.filter((item) => !seen.has(item.id))];
      });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const toast = useCallback((title: string, description?: string, tone: Toast["tone"] = "default") => {
    const id = `t-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [...prev, { id, title, description, tone }]);
    const timer = window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4200);
    timers.current.push(timer);
  }, []);

  useEffect(() => () => timers.current.forEach((t) => window.clearTimeout(t)), []);

  const navigate = useCallback((next: View) => {
    setView(next);
    setOpenEvidenceId(null);
    setSearchOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const openEvidence = useCallback((id: string) => setOpenEvidenceId(id), []);
  const closeEvidence = useCallback(() => setOpenEvidenceId(null), []);

  const uploadFiles = useCallback(
    (files: File[], meta?: UploadMeta) => {
      const accepted = files.slice(0, 12);
      accepted.forEach((file) => {
        void (async () => {
          let upload: { id: string; hash: string };
          try {
            upload = await api.upload(file, meta);
          } catch (error) {
            toast(
              "Upload failed",
              error instanceof Error ? error.message : `${file.name} could not be preserved.`,
              "danger",
            );
            return;
          }
          const { id, hash } = upload;
          const url = file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined;
          const tags = Array.from(
            new Set([
              "new intake",
              ...(meta?.location ? [meta.location] : []),
              ...(meta?.persons ?? []),
            ]),
          ).slice(0, 6);
          const item: EvidenceItem = {
            id,
            name: file.name,
            type: inferType(file),
            mime: file.type || "application/octet-stream",
            size: file.size,
            uploadedAt: new Date().toISOString(),
            uploadedBy: "Aarav Shah",
            status: "queued",
            source: "Local upload",
            hash,
            tags,
            personIds: [],
            eventIds: [],
            note:
              meta?.note ||
              "Added in this session. Awaiting entity extraction and relationship mapping.",
            preview: `${file.type || "binary"} · ${formatBytes(file.size)}`,
            url,
            integrity: "pending",
            occurredAt: meta?.date ? `${meta.date}T${meta.time || "00:00"}` : undefined,
            location: meta?.location,
            persons: meta?.persons ?? [],
            captureNote: meta?.note,
          };
          setEvidence((prev) => [item, ...prev]);
          setUploads((prev) => ({ ...prev, [id]: 2 }));
          setAuditLogs((prev) => [
            {
              id: `a-${id}`,
              actor: "Aarav Shah",
              action: "Uploaded evidence",
              target: file.name,
              at: new Date().toISOString(),
              ip: "10.24.8.112",
              result: "success",
            },
            ...prev,
          ]);
          toast("Evidence preserved", `${file.name} hashed and queued for processing.`, "success");

          // Poll the backend until processing finishes.
          let attempts = 0;
          const tick = window.setInterval(async () => {
            attempts += 1;
            try {
              const status = await api.evidenceStatus(id);
              const progress = Math.max(2, Math.round(status.progress));
              setUploads((prev) => ({ ...prev, [id]: progress }));
              setEvidence((prev) =>
                prev.map((e) =>
                  e.id === id
                    ? { ...e, status: mapStatus(status.status), integrity: mapIntegrity(status.integrity) }
                    : e,
                ),
              );
              if (status.status === "completed" || status.status === "failed") {
                window.clearInterval(tick);
                setUploads((prev) => ({ ...prev, [id]: 100 }));
                if (status.status === "completed") {
                  try {
                    const fresh = await api.evidence(id);
                    setEvidence((prev) => prev.map((e) => (e.id === id ? { ...fresh, url: e.url } : e)));
                  } catch {
                    // Keep the optimistic item if the refresh fails.
                  }
                  setNotifications((prev) => [
                    {
                      id: `n-${id}`,
                      title: "Processing complete",
                      body: `${file.name} · entities extracted · integrity ${mapIntegrity(status.integrity)}.`,
                      at: new Date().toISOString(),
                      read: false,
                      kind: "processing",
                    },
                    ...prev,
                  ]);
                  toast("Processing complete", `${file.name} is now searchable.`, "success");
                } else {
                  toast("Processing failed", status.error ?? `${file.name} could not be processed.`, "danger");
                }
              }
            } catch {
              // Item may still be registering; keep polling briefly.
              if (attempts >= 150) window.clearInterval(tick);
            }
          }, 2000);
          timers.current.push(tick);
        })();
      });
    },
    [toast],
  );

  const deleteEvidence = useCallback(
    async (id: string) => {
      const item = evidence.find((entry) => entry.id === id);
      try {
        await api.deleteEvidence(id);
      } catch (error) {
        toast(
          "Delete failed",
          error instanceof Error ? error.message : "The item could not be removed.",
          "danger",
        );
        return;
      }
      setEvidence((prev) => prev.filter((entry) => entry.id !== id));
      setUploads((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      setOpenEvidenceId((current) => (current === id ? null : current));
      setAuditLogs((prev) => [
        {
          id: `a-del-${id}`,
          actor: "Aarav Shah",
          action: "Removed evidence",
          target: item?.name ?? id,
          at: new Date().toISOString(),
          ip: "10.24.8.112",
          result: "warning",
        },
        ...prev,
      ]);
      toast(
        "Evidence removed",
        `${item?.name ?? "Item"} removed from the active vault. Original retained for custody.`,
        "success",
      );
    },
    [evidence, toast],
  );

  const markRead = useCallback((id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const reviewInsight = useCallback((id: string) => {
    setInsights((prev) => prev.map((i) => (i.id === id ? { ...i, reviewed: true } : i)));
  }, []);

  const ask = useCallback(
    (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;
      const userMsg: ChatMessage = { id: `m-${Date.now()}`, role: "user", text: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setThinking(true);
      const generation = chatGeneration.current;
      answer(trimmed)
        .then((reply) => {
          if (generation !== chatGeneration.current) return;
          setMessages((prev) => [
            ...prev,
            {
              id: `m-${Date.now()}-r`,
              role: "assistant",
              text: reply.text,
              citations: reply.citations,
            },
          ]);
        })
        .catch((error: unknown) => {
          if (generation !== chatGeneration.current) return;
          const detail = error instanceof Error ? error.message : "Unexpected error";
          setMessages((prev) => [
            ...prev,
            {
              id: `m-${Date.now()}-r`,
              role: "assistant",
              text: `I couldn't reach the evidence engine.\n\n${detail}\n\nMake sure the backend is running and try again.`,
            },
          ]);
          toast("Assistant unavailable", "The evidence engine could not be reached.", "danger");
        })
        .finally(() => {
          if (generation === chatGeneration.current) setThinking(false);
        });
    },
    [toast],
  );

  const clearChat = useCallback(() => {
    chatGeneration.current += 1;
    setMessages([]);
    setThinking(false);
  }, []);

  const value = useMemo<AppContextValue>(
    () => ({
      view,
      navigate,
      theme,
      toggleTheme: () => setTheme((t) => (t === "light" ? "dark" : "light")),
      evidence,
      people,
      events,
      pipeline,
      insights,
      notifications,
      auditLogs,
      unreadCount: notifications.filter((n) => !n.read).length,
      markRead,
      markAllRead,
      reviewInsight,
      openEvidenceId,
      openEvidence,
      closeEvidence,
      selectedPersonId,
      selectPerson: setSelectedPersonId,
      searchOpen,
      setSearchOpen,
      uploads,
      uploadFiles,
      deleteEvidence,
      messages,
      thinking,
      ask,
      clearChat,
      toasts,
      toast,
    }),
    [
      view,
      navigate,
      theme,
      evidence,
      insights,
      notifications,
      auditLogs,
      markRead,
      markAllRead,
      reviewInsight,
      openEvidenceId,
      openEvidence,
      closeEvidence,
      selectedPersonId,
      searchOpen,
      uploads,
      uploadFiles,
      deleteEvidence,
      messages,
      thinking,
      ask,
      clearChat,
      toasts,
      toast,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
