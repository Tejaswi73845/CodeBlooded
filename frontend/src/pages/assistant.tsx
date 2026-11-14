import {
  ArrowUp,
  Check,
  Copy,
  FileText,
  Plus,
  ShieldCheck,
  Sparkles,
  Square,
  Wand2,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "@/store/app-store";
import { suggestedPrompts } from "@/lib/assistant";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileTypeTile } from "@/components/evidence/file-type";
import { PersonAvatar } from "@/components/person-avatar";

function Inline({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**"))
          return (
            <strong key={i} className="font-semibold text-ink">
              {part.slice(2, -2)}
            </strong>
          );
        if (part.startsWith("`") && part.endsWith("`"))
          return (
            <code key={i} className="rounded bg-surface-3 px-1 py-px font-mono text-[11px] text-ink-2">
              {part.slice(1, -1)}
            </code>
          );
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function Answer({ text }: { text: string }) {
  return (
    <div className="space-y-2">
      {text.split("\n").map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-0.5" />;
        if (line.startsWith("• "))
          return (
            <div key={i} className="flex gap-2">
              <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-ink-3" />
              <p className="flex-1 text-[13px] leading-relaxed text-ink-2">
                <Inline text={line.slice(2)} />
              </p>
            </div>
          );
        return (
          <p key={i} className="text-[13px] leading-relaxed text-ink-2">
            <Inline text={line} />
          </p>
        );
      })}
    </div>
  );
}

export function AssistantPage() {
  const { messages, thinking, ask, clearChat, evidence, events, openEvidence, people, toast, workspace } = useApp();
  const [draft, setDraft] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const latestReply = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant"),
    [messages],
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  const submit = (text?: string) => {
    const value = (text ?? draft).trim();
    if (!value || thinking) return;
    ask(value);
    setDraft("");
  };

  const copy = async (id: string, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    toast("Copied", "Response copied to clipboard.");
    window.setTimeout(() => setCopiedId(null), 1600);
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={
          <>
            <Badge tone="violet">
              <Sparkles className="mr-0.5 h-3 w-3" /> Evidence-aware
            </Badge>
            <span className="text-[11px] text-ink-3">Grounded in {evidence.length} preserved items</span>
          </>
        }
        title="AI Assistant"
        description="Ask questions across the case. Every answer cites the preserved evidence it relies on."
        actions={
          <Button variant="secondary" onClick={() => { clearChat(); setDraft(""); }}>
            <Plus className="h-3.5 w-3.5" /> New chat
          </Button>
        }
      />

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="flex h-[calc(100dvh-210px)] min-h-[540px] flex-col overflow-hidden rounded-card border border-line bg-surface shadow-card">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-md bg-ink text-surface">
                <Sparkles className="h-3 w-3" />
              </span>
              <div>
                <p className="text-[12px] font-semibold leading-tight">Veritas Intelligence</p>
                <p className="text-[10px] leading-tight text-ink-3">Case {workspace.caseId} · evidence context</p>
              </div>
            </div>
            <Badge tone="neutral" className="hidden sm:inline-flex">
              <ShieldCheck className="mr-0.5 h-3 w-3 text-success" /> Evidence-grounded
            </Badge>
          </div>

          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
            {messages.length === 0 ? (
              <div className="mx-auto flex h-full max-w-xl flex-col justify-center px-5 py-8">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-surface-2 text-accent shadow-card">
                  <Sparkles className="h-5 w-5" />
                </div>
                <h2 className="mt-3 text-[19px] font-semibold tracking-[-0.02em]">Ask the evidence.</h2>
                <p className="mt-1 max-w-md text-[12.5px] leading-relaxed text-ink-2">
                  Summaries, inconsistencies, chronology and entity lookups across all preserved files in{" "}
                  {workspace.caseId}. Answers stay tied to their sources.
                </p>

                <div className="mt-5 grid gap-1.5 sm:grid-cols-2">
                  {suggestedPrompts().map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => submit(prompt)}
                      className="group flex items-start gap-2 rounded-xl border border-line bg-surface p-2.5 text-left transition-all hover:border-line-strong hover:shadow-card"
                    >
                      <Wand2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-3 group-hover:text-accent" />
                      <span className="text-[11.5px] leading-snug text-ink-2 group-hover:text-ink">{prompt}</span>
                    </button>
                  ))}
                </div>

                <div className="mt-5 flex items-center gap-2">
                  <span className="flex -space-x-1.5">
                    {people.slice(0, 4).map((p) => (
                      <PersonAvatar key={p.id} person={p} size="xs" ring />
                    ))}
                  </span>
                  <p className="text-[10.5px] text-ink-3">
                    {people.length} people, {events.length} events and {evidence.length} files indexed
                  </p>
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-[720px] space-y-5 px-4 py-5 sm:px-6">
                {messages.map((message) =>
                  message.role === "user" ? (
                    <div key={message.id} className="flex justify-end">
                      <div className="max-w-[85%] rounded-[16px] rounded-br-[5px] bg-accent px-3.5 py-2 text-[12.5px] leading-relaxed text-white shadow-sm">
                        {message.text}
                      </div>
                    </div>
                  ) : (
                    <div key={message.id} className="group flex gap-2.5">
                      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-line bg-surface-2 text-accent">
                        <Sparkles className="h-3.5 w-3.5" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[11.5px] font-semibold">Veritas</span>
                          <span className="text-[10px] text-ink-3">evidence-grounded</span>
                        </div>
                        <div className="mt-1.5">
                          <Answer text={message.text} />
                        </div>
                        {message.citations && message.citations.length > 0 && (
                          <div className="mt-2.5 flex flex-wrap gap-1">
                            {message.citations.map((id) => {
                              const item = evidence.find((e) => e.id === id);
                              if (!item) {
                                return (
                                  <span
                                    key={id}
                                    title={id}
                                    className="flex max-w-[210px] items-center gap-1 rounded-md border border-line bg-surface-2 px-1.5 py-0.5"
                                  >
                                    <FileText className="h-3 w-3 shrink-0 text-ink-3" />
                                    <span className="truncate text-[9.5px] text-ink-2">{id}</span>
                                  </span>
                                );
                              }
                              return (
                                <button
                                  key={id}
                                  onClick={() => openEvidence(id)}
                                  title={item.name}
                                  className="flex max-w-[210px] items-center gap-1 rounded-md border border-line bg-surface-2 py-0.5 pl-0.5 pr-1.5 transition-colors hover:border-line-strong hover:bg-surface-3"
                                >
                                  <FileTypeTile type={item.type} size="sm" />
                                  <span className="truncate text-[9.5px] text-ink-2">{item.name}</span>
                                </button>
                              );
                            })}
                          </div>
                        )}
                        <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                          <button
                            onClick={() => copy(message.id, message.text)}
                            className="flex h-6 items-center gap-1 rounded px-1.5 text-[10px] text-ink-3 hover:bg-surface-2 hover:text-ink"
                          >
                            {copiedId === message.id ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                            Copy
                          </button>
                          <button
                            onClick={() => toast("Added to report", "Response appended to the working draft.", "success")}
                            className="flex h-6 items-center gap-1 rounded px-1.5 text-[10px] text-ink-3 hover:bg-surface-2 hover:text-ink"
                          >
                            <FileText className="h-3 w-3" /> Add to report
                          </button>
                        </div>
                      </div>
                    </div>
                  ),
                )}

                {thinking && (
                  <div className="flex gap-2.5">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-line bg-surface-2 text-accent">
                      <Sparkles className="h-3.5 w-3.5" />
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[11.5px] font-semibold">Veritas</span>
                        <span className="text-[10px] text-ink-3">reviewing sources…</span>
                      </div>
                      <div className="mt-2 flex items-center gap-1.5">
                        {[0, 1, 2].map((i) => (
                          <span
                            key={i}
                            className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-3"
                            style={{ animationDelay: `${i * 160}ms` }}
                          />
                        ))}
                        <span className="ml-1 text-[10.5px] text-ink-3">
                          spanning timeline, chat exports and financial records
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="border-t border-line bg-surface px-3 pb-2.5 pt-2 sm:px-4">
            <div className="rounded-xl border border-line bg-surface-2 p-1.5 transition-colors focus-within:border-accent/50">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                rows={1}
                placeholder="Ask about this case — dates, people, inconsistencies…"
                aria-label="Ask the assistant"
                className="max-h-32 min-h-[30px] w-full resize-none bg-transparent px-2 py-1 text-[12.5px] leading-relaxed outline-none placeholder:text-ink-3"
              />
              <div className="flex items-center gap-1">
                <span className="text-[9.5px] text-ink-3">{evidence.length} sources in context</span>
                <div className="ml-auto flex items-center gap-1.5">
                  {thinking ? (
                    <Button variant="secondary" size="sm" disabled>
                      <Square className="h-3 w-3" /> Stop
                    </Button>
                  ) : (
                    <button
                      onClick={() => submit()}
                      disabled={!draft.trim()}
                      aria-label="Send message"
                      className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-white transition-opacity disabled:opacity-35"
                    >
                      <ArrowUp className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
            <p className="mt-1.5 px-1 text-[9.5px] text-ink-3">
              Responses cite preserved evidence. Verify before disclosure — AI output is not itself evidence.
            </p>
          </div>
        </div>

        <aside className="hidden flex-col gap-3 lg:flex">
          <div className="rounded-card border border-line bg-surface p-4 shadow-card">
            <div className="flex items-center justify-between">
              <h3 className="text-[12px] font-semibold">Session context</h3>
              <Badge tone="success" dot>
                Live
              </Badge>
            </div>
            <dl className="mt-2.5 space-y-1.5 text-[11px]">
              {[
                ["Case", workspace.caseId],
                ["Files", `${evidence.length} preserved`],
                ["Events", `${events.length} reconstructed`],
                ["People", `${people.length} resolved`],
                ["Integrity", `${evidence.filter((e) => e.integrity === "verified").length} / ${evidence.length} verified`],
              ].map(([k, v]) => (
                <div key={k} className="flex items-center justify-between">
                  <dt className="text-ink-3">{k}</dt>
                  <dd className="font-medium">{v}</dd>
                </div>
              ))}
            </dl>
          </div>

          {messages.length > 0 && (
            <div className="rounded-card border border-line bg-surface p-4 shadow-card">
              <h3 className="text-[12px] font-semibold">Suggested prompts</h3>
              <div className="mt-2 space-y-1">
                {suggestedPrompts().map((p) => (
                  <button
                    key={p}
                    onClick={() => submit(p)}
                    className="flex w-full items-start gap-1.5 rounded-lg px-1.5 py-1.5 text-left text-[11px] leading-snug text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink"
                  >
                    <Wand2 className="mt-0.5 h-3 w-3 shrink-0 text-ink-3" />
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {latestReply && (
            <div className="rounded-card border border-line bg-surface p-4 shadow-card">
              <div className="flex items-center justify-between">
                <h3 className="text-[12px] font-semibold">Sources used</h3>
                <Badge tone="neutral">{latestReply.sources?.length ?? 0}</Badge>
              </div>
              <p className="mt-0.5 text-[10px] text-ink-3">Pulled from the last answer</p>
              {latestReply.sources && latestReply.sources.length > 0 ? (
                <ul className="mt-2 max-h-[330px] space-y-1.5 overflow-y-auto pr-0.5">
                  {latestReply.sources.map((source, index) => {
                    const item = evidence.find((entry) => entry.id === source.evidenceId);
                    return (
                      <li key={`${source.evidenceId}-${source.locator ?? index}-${index}`}>
                        <button
                          onClick={() => item && openEvidence(item.id)}
                          disabled={!item}
                          className="w-full rounded-lg border border-line bg-surface-2/50 p-2 text-left transition-colors enabled:hover:border-line-strong enabled:hover:bg-surface-2"
                        >
                          <span className="flex items-center gap-2">
                            <FileTypeTile type={item?.type ?? "document"} size="sm" />
                            <span className="min-w-0 flex-1 truncate text-[10.5px] font-medium">
                              {source.name}
                            </span>
                            <span className="shrink-0 text-[9.5px] text-ink-3">
                              {Math.round(source.relevance * 100)}%
                            </span>
                          </span>
                          <span className="mt-1 line-clamp-2 block text-[10px] leading-relaxed text-ink-3">
                            {source.excerpt}
                          </span>
                          {source.locator && (
                            <span className="mt-0.5 block text-[9.5px] text-ink-3">{source.locator}</span>
                          )}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="mt-2 text-[10.5px] leading-relaxed text-ink-3">
                  The last answer didn&rsquo;t use any preserved evidence sources.
                </p>
              )}
            </div>
          )}

          <p className="flex items-start gap-1.5 px-1 text-[10px] leading-relaxed text-ink-3">
            <ShieldCheck className="mt-px h-3 w-3 shrink-0 text-success" />
            Answers are generated from preserved evidence through the configured AI provider.
          </p>
        </aside>
      </div>
    </div>
  );
}
