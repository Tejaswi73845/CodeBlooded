import {
  Background,
  BackgroundVariant,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  ArrowRight,
  Building2,
  CalendarClock,
  ChevronRight,
  Focus,
  Mail,
  MessageSquare,
  Minus,
  Phone,
  Plus,
  Search,
  Sparkles,
  UserRound,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useApp } from "@/store/app-store";
import type { GraphNode } from "@/data/types";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PersonAvatar } from "@/components/person-avatar";
import { FileTypeTile } from "@/components/evidence/file-type";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type GraphNodeData = GraphNode & {
  tint?: string;
  risk?: "low" | "medium" | "high";
  evidenceIds?: string[];
} & Record<string, unknown>;

const positions: Record<string, { x: number; y: number }> = {
  "g-p2": { x: 500, y: 330 },
  "g-p1": { x: 735, y: 215 },
  "g-p5": { x: 700, y: 455 },
  "g-p4": { x: 900, y: 320 },
  "g-p7": { x: 885, y: 520 },
  "g-p3": { x: 300, y: 495 },
  "g-p6": { x: 285, y: 180 },
  "g-p8": { x: 105, y: 330 },
  "g-phone1": { x: 715, y: 88 },
  "g-email1": { x: 930, y: 160 },
  "g-phone5": { x: 690, y: 610 },
  "g-email4": { x: 1030, y: 405 },
  "g-phone2": { x: 400, y: 640 },
  "g-conv1": { x: 535, y: 130 },
  "g-conv2": { x: 1000, y: 250 },
  "g-conv3": { x: 905, y: 55 },
  "g-event1": { x: 355, y: 85 },
  "g-event2": { x: 500, y: 555 },
  "g-event3": { x: 1040, y: 560 },
  "g-event4": { x: 120, y: 505 },
};

const edgeStyle = "var(--line-strong)";

function PersonNode({ data, selected }: NodeProps<Node<GraphNodeData>>) {
  return (
    <div
      className={cn(
        "w-[184px] rounded-xl border bg-surface px-2.5 py-2 shadow-card transition-shadow",
        selected ? "border-accent shadow-[0_0_0_3px_var(--accent-soft)]" : "border-line",
      )}
    >
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <div className="flex items-center gap-2">
        <PersonAvatar person={{ name: data.label, tint: data.tint ?? "#007AFF" }} size="md" />
        <div className="min-w-0">
          <p className="truncate text-[12px] font-semibold leading-tight">{data.label}</p>
          <p className="mt-0.5 truncate text-[10px] leading-tight text-ink-3">{data.sublabel}</p>
        </div>
      </div>
      <div className="mt-1.5 flex items-center gap-1 border-t border-line pt-1.5 text-[9.5px] text-ink-3">
        <span
          className={cn(
            "h-1 w-1 rounded-full",
            data.risk === "high" ? "bg-danger" : data.risk === "medium" ? "bg-warning" : "bg-success",
          )}
        />
        {data.evidenceIds?.length ?? 0} linked files
      </div>
    </div>
  );
}

const entityIcons = {
  phone: Phone,
  email: Mail,
  conversation: MessageSquare,
  event: CalendarClock,
} as const;

function EntityNode({ data, selected }: NodeProps<Node<GraphNodeData>>) {
  const Icon = entityIcons[data.kind as keyof typeof entityIcons] ?? Building2;
  return (
    <div
      className={cn(
        "w-[176px] rounded-[10px] border bg-surface px-2 py-1.5 shadow-card",
        selected ? "border-accent shadow-[0_0_0_3px_var(--accent-soft)]" : "border-line",
      )}
    >
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <div className="flex items-center gap-1.5">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-3 text-ink-2">
          <Icon className="h-3 w-3" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-[11px] font-medium leading-tight">{data.label}</p>
          {data.sublabel && (
            <p className="mt-0.5 truncate text-[9.5px] leading-tight text-ink-3">{data.sublabel}</p>
          )}
        </div>
      </div>
    </div>
  );
}

const nodeTypes = { person: PersonNode, entity: EntityNode };

function GraphToolbar() {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  return (
    <div className="absolute left-3 top-3 z-10 flex items-center gap-0.5 rounded-lg border border-line bg-surface/95 p-0.5 shadow-card backdrop-blur">
      <button
        onClick={() => zoomOut()}
        aria-label="Zoom out"
        className="flex h-7 w-7 items-center justify-center rounded-md text-ink-2 hover:bg-surface-3"
      >
        <Minus className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={() => zoomIn()}
        aria-label="Zoom in"
        className="flex h-7 w-7 items-center justify-center rounded-md text-ink-2 hover:bg-surface-3"
      >
        <Plus className="h-3.5 w-3.5" />
      </button>
      <span className="mx-0.5 h-4 w-px bg-line" />
      <button
        onClick={() => fitView({ padding: 0.15, duration: 400 })}
        aria-label="Fit graph"
        className="flex h-7 w-7 items-center justify-center rounded-md text-ink-2 hover:bg-surface-3"
      >
        <Focus className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export function PeoplePage() {
  const { people, evidence, openEvidence, selectedPersonId, selectPerson, navigate, ask } = useApp();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches,
  );
  const [visibleKinds, setVisibleKinds] = useState<Record<string, boolean>>({
    person: true,
    phone: true,
    email: true,
    conversation: true,
    event: true,
  });

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const onChange = () => setIsDesktop(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const selected = selectedPersonId && !selectedId ? `g-${selectedPersonId}` : selectedId;

  const graph = useMemo(() => {
    const nodes: Node<GraphNodeData>[] = [];
    people.forEach((p, index) => {
      const fallbackAngle = (index / Math.max(people.length, 1)) * Math.PI * 2;
      const fallback = { x: 560 + Math.cos(fallbackAngle) * 340, y: 380 + Math.sin(fallbackAngle) * 300 };
      nodes.push({
        id: `g-${p.id}`,
        type: "person",
        position: positions[`g-${p.id}`] ?? fallback,
        data: { id: p.id, kind: "person", label: p.name, sublabel: p.role, tint: p.tint, risk: p.risk, personId: p.id, evidenceIds: evidence.filter((e) => e.personIds.includes(p.id)).map((e) => e.id) },
        width: 184,
        hidden: !visibleKinds.person,
      });
    });

    const edge = (
      id: string,
      source: string,
      target: string,
      tone: "contact" | "device" | "money" = "contact",
    ): Edge => ({
      id,
      source,
      target,
      style: {
        stroke: tone === "device" ? "var(--violet)" : tone === "money" ? "var(--success)" : edgeStyle,
        strokeWidth: 1.3,
        strokeDasharray: tone === "contact" ? undefined : "4 3",
      },
      markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12, color: tone === "device" ? "var(--violet)" : tone === "money" ? "var(--success)" : "var(--line-strong)" },
      hidden:
        !visibleKinds[nodes.find((n) => n.id === source)?.data.kind ?? "person"] ||
        !visibleKinds[nodes.find((n) => n.id === target)?.data.kind ?? "person"],
    });

    const edges: Edge[] = [];

    // Connect detected people who appear in the same evidence item.
    const isDetected = (id: string) => !/^p\d+$/.test(id);
    const peopleByEvidence = new Map<string, string[]>();
    people.forEach((p) => {
      evidence.forEach((e) => {
        if (!e.personIds.includes(p.id)) return;
        const list = peopleByEvidence.get(e.id) ?? [];
        list.push(`g-${p.id}`);
        peopleByEvidence.set(e.id, list);
      });
    });
    for (const [evidenceId, ids] of peopleByEvidence) {
      const unique = Array.from(new Set(ids));
      if (!unique.some((id) => isDetected(id.replace("g-", "")))) continue;
      for (let index = 1; index < unique.length; index += 1) {
        edges.push(edge(`dyn-${evidenceId}-${index}`, unique[0], unique[index]));
      }
    }

    return { nodes, edges };
  }, [people, evidence, visibleKinds]);

  const selectedNode = graph.nodes.find((n) => n.id === selected);
  const neighbors = useMemo(() => {
    if (!selected) return [];
    const ids = new Set<string>();
    graph.edges.forEach((e) => {
      if (e.hidden) return;
      if (e.source === selected) ids.add(e.target);
      if (e.target === selected) ids.add(e.source);
    });
    return graph.nodes.filter((n) => ids.has(n.id));
  }, [graph, selected]);

  const q = query.trim().toLowerCase();
  const visibleNodes = useMemo(
    () => graph.nodes.map((n) => ({ ...n, hidden: n.hidden || (q !== "" && !n.data.label.toLowerCase().includes(q)) })),
    [graph.nodes, q],
  );
  const visibleEdges = useMemo(() => {
    const shown = new Set(visibleNodes.filter((n) => !n.hidden).map((n) => n.id));
    return graph.edges.map((e) => ({ ...e, hidden: e.hidden || !shown.has(e.source) || !shown.has(e.target) }));
  }, [graph.edges, visibleNodes]);

  const relatedEvidence = useMemo(() => {
    const ids = selectedNode?.data.evidenceIds ?? [];
    return evidence.filter((e) => ids.includes(e.id));
  }, [selectedNode, evidence]);

  const selectedPerson = selectedNode?.data.personId
    ? people.find((p) => p.id === selectedNode.data.personId)
    : undefined;

  const clearSelection = () => {
    setSelectedId(null);
    selectPerson(null);
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={
          <>
            <Badge tone="violet" dot>
              {people.length} people · {graph.edges.length} connections
            </Badge>
            <span className="text-[11px] text-ink-3">{evidence.length} evidence items linked</span>
          </>
        }
        title="People & Connections"
        description="Entities resolved from metadata, conversation and physical evidence. Select a node to inspect its evidence and relationships."
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate("assistant")}>
              <Sparkles className="h-3.5 w-3.5 text-accent" /> Analyse network
            </Button>
            <Button variant="primary" onClick={() => navigate("vault")}>
              <ArrowRight className="h-3.5 w-3.5" /> Open vault
            </Button>
          </>
        }
      />

      <div className="relative">
        <div className="overflow-hidden rounded-card border border-line bg-surface shadow-card">
          <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2.5">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-ink-3" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Find entity…"
                aria-label="Find entity in graph"
                className="h-7 w-full rounded-lg border border-line bg-surface-2 pl-7 pr-2 text-[11.5px] outline-none sm:w-[170px]"
              />
            </div>
            <div className="flex flex-wrap items-center gap-1">
              {(
                [
                  ["person", "People"],
                  ["phone", "Phones"],
                  ["email", "Emails"],
                  ["conversation", "Conversations"],
                  ["event", "Events"],
                ] as const
              ).map(([kind, label]) => (
                <button
                  key={kind}
                  onClick={() => setVisibleKinds((v) => ({ ...v, [kind]: !v[kind] }))}
                  aria-pressed={visibleKinds[kind]}
                  className={cn(
                    "h-6 rounded-full px-2 text-[10.5px] font-medium transition-colors",
                    visibleKinds[kind]
                      ? "bg-surface-3 text-ink"
                      : "bg-transparent text-ink-3 line-through hover:text-ink-2",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="ml-auto hidden items-center gap-2.5 text-[10px] text-ink-3 sm:flex">
              <span className="inline-flex items-center gap-1">
                <span className="h-px w-4 bg-line-strong" /> contact
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-px w-4 border-t border-dashed border-violet" /> device
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-px w-4 border-t border-dashed border-success" /> funds
              </span>
            </span>
          </div>

          <div className="relative h-[500px] w-full bg-[radial-gradient(circle_at_1px_1px,var(--line)_1px,transparent_0)] [background-size:22px_22px] lg:h-[660px]">
            <ReactFlowProvider>
              <GraphToolbar />
              <ReactFlow
                nodes={visibleNodes}
                edges={visibleEdges}
                nodeTypes={nodeTypes}
                onNodeClick={(_, node) => setSelectedId(node.id)}
                onPaneClick={clearSelection}
                fitView={isDesktop}
                fitViewOptions={{ padding: 0.08 }}
                defaultViewport={isDesktop ? undefined : { x: -210, y: 10, zoom: 0.8 }}
                minZoom={0.35}
                maxZoom={1.6}
                nodesDraggable
                nodesConnectable={false}
                elementsSelectable
                proOptions={{ hideAttribution: true }}
                defaultEdgeOptions={{ type: "default" }}
              >
                <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--line-strong)" />
              </ReactFlow>
            </ReactFlowProvider>
          </div>
        </div>

        {selectedNode && (
          <div className="ml-3 mr-3 mb-3 flex max-h-[560px] flex-col overflow-hidden rounded-card border border-line bg-surface shadow-card lg:absolute lg:right-0 lg:top-[56px] lg:z-20 lg:m-0 lg:max-h-[620px] lg:w-[344px] lg:shadow-pop">
            <>
              <div className="flex items-start gap-2.5 border-b border-line p-4">
                {selectedPerson ? (
                  <PersonAvatar person={selectedPerson} size="lg" />
                ) : (
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-3 text-ink-2">
                    {selectedNode.data.kind === "event" ? (
                      <CalendarClock className="h-[18px] w-[18px]" />
                    ) : selectedNode.data.kind === "conversation" ? (
                      <MessageSquare className="h-[18px] w-[18px]" />
                    ) : selectedNode.data.kind === "email" ? (
                      <Mail className="h-[18px] w-[18px]" />
                    ) : (
                      <Phone className="h-[18px] w-[18px]" />
                    )}
                  </span>
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-[13.5px] font-semibold leading-tight">{selectedNode.data.label}</p>
                  <p className="mt-0.5 text-[11px] text-ink-2">{selectedNode.data.sublabel}</p>
                  {selectedPerson && (
                    <div className="mt-1.5 flex items-center gap-1.5">
                      <Badge
                        tone={
                          selectedPerson.risk === "high"
                            ? "danger"
                            : selectedPerson.risk === "medium"
                              ? "warning"
                              : "success"
                        }
                      >
                        {selectedPerson.risk} risk
                      </Badge>
                      <Badge tone="neutral">{selectedPerson.evidenceCount} files</Badge>
                    </div>
                  )}
                </div>
                <button
                  onClick={clearSelection}
                  aria-label="Clear selection"
                  className="text-[11px] text-ink-3 hover:text-ink"
                >
                  Close
                </button>
              </div>

              <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
                {selectedPerson && (
                  <>
                    <div className="space-y-1.5">
                      {selectedPerson.phone && (
                        <p className="flex items-center gap-2 text-[11.5px] text-ink-2">
                          <Phone className="h-3 w-3 text-ink-3" /> {selectedPerson.phone}
                        </p>
                      )}
                      {selectedPerson.email && (
                        <p className="flex items-center gap-2 text-[11.5px] text-ink-2">
                          <Mail className="h-3 w-3 text-ink-3" /> {selectedPerson.email}
                        </p>
                      )}
                      <p className="flex items-center gap-2 text-[11.5px] text-ink-2">
                        <Users className="h-3 w-3 text-ink-3" /> {selectedPerson.role} · {selectedPerson.location}
                      </p>
                    </div>
                    <p className="rounded-lg border border-line bg-surface-2 p-2.5 text-[11.5px] leading-relaxed text-ink-2">
                      {selectedPerson.note}
                    </p>
                  </>
                )}

                <section>
                  <h3 className="mb-1.5 text-[10.5px] font-medium uppercase tracking-[0.05em] text-ink-3">
                    Connections · {neighbors.length}
                  </h3>
                  <ul className="space-y-0.5">
                    {neighbors.slice(0, 7).map((n) => (
                      <li key={n.id}>
                        <button
                          onClick={() => setSelectedId(n.id)}
                          className="flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left transition-colors hover:bg-surface-2"
                        >
                          <span className="flex h-5 w-5 items-center justify-center rounded bg-surface-3 text-[9px] font-medium text-ink-2">
                            {n.data.kind === "person" ? (
                              <UserRound className="h-2.5 w-2.5" />
                            ) : n.data.kind === "event" ? (
                              <CalendarClock className="h-2.5 w-2.5" />
                            ) : n.data.kind === "conversation" ? (
                              <MessageSquare className="h-2.5 w-2.5" />
                            ) : (
                              <Phone className="h-2.5 w-2.5" />
                            )}
                          </span>
                          <span className="min-w-0 flex-1 truncate text-[11.5px]">{n.data.label}</span>
                          <ChevronRight className="h-3 w-3 text-ink-3" />
                        </button>
                      </li>
                    ))}
                    {neighbors.length === 0 && (
                      <li className="text-[11px] text-ink-3">No visible connections under current filters.</li>
                    )}
                  </ul>
                </section>

                <section>
                  <h3 className="mb-1.5 text-[10.5px] font-medium uppercase tracking-[0.05em] text-ink-3">
                    Related evidence
                  </h3>
                  <ul className="space-y-1">
                    {relatedEvidence.slice(0, 4).map((item) => (
                      <li key={item.id}>
                        <button
                          onClick={() => openEvidence(item.id)}
                          className="flex w-full items-center gap-2 rounded-lg border border-line px-2 py-1.5 text-left transition-colors hover:bg-surface-2"
                        >
                          <FileTypeTile type={item.type} size="sm" />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-[10.5px] font-medium">{item.name}</span>
                            <span className="block text-[9.5px] text-ink-3">{formatDate(item.uploadedAt)}</span>
                          </span>
                          <ChevronRight className="h-3 w-3 shrink-0 text-ink-3" />
                        </button>
                      </li>
                    ))}
                    {relatedEvidence.length === 0 && (
                      <li className="text-[11px] text-ink-3">No preserved file is linked to this node yet.</li>
                    )}
                  </ul>
                </section>
              </div>

              <div className="border-t border-line p-3">
                <Button
                  variant="soft"
                  className="w-full"
                  onClick={() => {
                    const label = selectedNode.data.label;
                    ask(
                      selectedPerson
                        ? `Show all evidence involving ${selectedPerson.name}.`
                        : `Show the relationships connected to ${label}.`,
                    );
                    navigate("assistant");
                  }}
                >
                  <Sparkles className="h-3.5 w-3.5" /> Ask about this node
                </Button>
              </div>
            </>
          </div>
        )}

        <div className="mx-3 mb-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border border-line bg-surface-2 px-3 py-2 text-[10.5px] text-ink-3 lg:absolute lg:bottom-3 lg:left-3 lg:z-10 lg:m-0 lg:bg-surface/95 lg:shadow-card lg:backdrop-blur">
          <span className="inline-flex items-center gap-1">
            <Users className="h-3 w-3" /> <b className="font-semibold text-ink-2">{people.length}</b> people
          </span>
          <span>
            <b className="font-semibold text-ink-2">{graph.edges.length}</b> connections
          </span>
          <span className="hidden sm:inline">Select a node to inspect its evidence</span>
        </div>
      </div>
    </div>
  );
}
