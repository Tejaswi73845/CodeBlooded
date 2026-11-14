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
import type { EvidenceItem, EvidenceType, Insight } from "@/data/types";
import { api } from "@/lib/api";
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
  uploadFiles: (files: File[]) => void;
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
    (files: File[]) => {
      const accepted = files.slice(0, 12);
      accepted.forEach(async (file) => {
        const { id, hash } = await api.upload(file);
        const url = file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined;
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
          tags: ["new intake"],
          personIds: [],
          eventIds: [],
          note: "Added in this session. Awaiting entity extraction and relationship mapping.",
          preview: `${file.type || "binary"} · ${formatBytes(file.size)}`,
          url,
          integrity: "pending",
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

        let progress = 2;
        const tick = window.setInterval(() => {
          progress = Math.min(100, progress + Math.random() * 18 + 6);
          setUploads((prev) => ({ ...prev, [id]: Math.round(progress) }));
          if (progress < 100 && progress > 25) {
            setEvidence((prev) =>
              prev.map((e) => (e.id === id && e.status === "queued" ? { ...e, status: "processing" } : e)),
            );
          }
          if (progress >= 100) {
            window.clearInterval(tick);
            setEvidence((prev) =>
              prev.map((e) => (e.id === id ? { ...e, status: "processed", integrity: "verified" } : e)),
            );
            setNotifications((prev) => [
              {
                id: `n-${id}`,
                title: "Processing complete",
                body: `${file.name} · entities extracted · SHA-256 verified.`,
                at: new Date().toISOString(),
                read: false,
                kind: "processing",
              },
              ...prev,
            ]);
            toast("Processing complete", `${file.name} is now searchable.`, "success");
          }
        }, 420);
        timers.current.push(tick);
      });
    },
    [toast],
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
      const timer = window.setTimeout(() => {
        if (generation !== chatGeneration.current) return;
        const reply = answer(trimmed);
        setMessages((prev) => [
          ...prev,
          {
            id: `m-${Date.now()}-r`,
            role: "assistant",
            text: reply.text,
            citations: reply.citations,
          },
        ]);
        setThinking(false);
      }, 1100);
      timers.current.push(timer);
    },
    [],
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
