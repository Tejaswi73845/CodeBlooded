import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  ChevronsUpDown,
  Check,
  FolderClosed,
  LayoutGrid,
  Network,
  Pencil,
  Plus,
  Settings,
  ShieldCheck,
  Sparkles,
  FileText,
  ScrollText,
  Timer,
  Trash2,
} from "lucide-react";
import { useApp, type View } from "@/store/app-store";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const navigation: { id: View; label: string; icon: typeof LayoutGrid }[] = [
  { id: "overview", label: "Overview", icon: LayoutGrid },
  { id: "vault", label: "Evidence Vault", icon: FolderClosed },
  { id: "timeline", label: "Timeline", icon: Timer },
  { id: "people", label: "People & Connections", icon: Network },
  { id: "assistant", label: "AI Assistant", icon: Sparkles },
  { id: "reports", label: "Reports", icon: FileText },
];

const utilityNav: { id: View; label: string; icon: typeof LayoutGrid }[] = [
  { id: "audit", label: "Audit Logs", icon: ScrollText },
  { id: "settings", label: "Settings", icon: Settings },
];

export function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-9 w-9 items-center justify-center rounded-full border border-accent/25 bg-accent text-on-accent shadow-[inset_0_1px_0_rgba(255,255,255,0.16),0_1px_3px_rgba(60,25,25,0.25)]">
        <span className="font-serif text-[18px] font-medium leading-none">V</span>
      </div>
      <div className="leading-none">
        <div className="font-serif text-[19px] font-medium tracking-[-0.015em]">Veritas</div>
        <div className="mt-[5px] text-[10px] font-medium tracking-[0.01em] text-ink-3">
          Evidence intelligence
        </div>
      </div>
    </div>
  );
}

function WorkspaceSwitch() {
  const {
    workspace,
    workspaces,
    activeWorkspaceId,
    switchWorkspace,
    createWorkspace,
    renameWorkspace,
    deleteWorkspace,
  } = useApp();
  const [mode, setMode] = useState<"create" | "rename" | "delete" | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const initials =
    workspace.name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase() ?? "")
      .join("") || "WS";

  const close = () => {
    if (!busy) setMode(null);
  };

  const submit = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setBusy(true);
    const ok =
      mode === "create"
        ? await createWorkspace(trimmed)
        : mode === "rename"
          ? await renameWorkspace(workspace.id, trimmed)
          : false;
    setBusy(false);
    if (ok) setMode(null);
  };

  const confirmDelete = async () => {
    setBusy(true);
    const ok = await deleteWorkspace(workspace.id);
    setBusy(false);
    if (ok) setMode(null);
  };

  return (
    <>
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button className="group flex w-full items-center gap-2.5 rounded-[9px] border border-line bg-surface-2/60 px-2.5 py-2 text-left transition-colors hover:border-line-strong hover:bg-surface-2">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[5px] bg-ink font-mono text-[9.5px] font-medium text-surface">
              {initials}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[12px] font-medium leading-tight">{workspace.name}</span>
              <span className="mt-[3px] block truncate font-mono text-[9.5px] leading-tight text-ink-3">
                {workspace.caseId}
                {workspace.isDefault ? " · default" : ""}
              </span>
            </span>
            <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-ink-3" />
          </button>
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content
            sideOffset={6}
            className="z-50 min-w-[252px] rounded-[10px] border border-line-strong/60 bg-surface p-1 shadow-pop data-[state=open]:animate-scale-in"
          >
            <DropdownMenu.Label className="px-2 py-1.5 text-[10.5px] font-medium text-ink-3">
              Workspaces
            </DropdownMenu.Label>
            {workspaces.map((item) => (
              <DropdownMenu.Item
                key={item.id}
                className="flex cursor-default items-center gap-2 rounded-[7px] px-2 py-1.5 text-[12.5px] outline-none data-[highlighted]:bg-surface-3"
                onSelect={() => void switchWorkspace(item.id)}
              >
                {item.id === activeWorkspaceId ? (
                  <Check className="h-3.5 w-3.5 text-accent" />
                ) : (
                  <span className="h-3.5 w-3.5" />
                )}
                <span className="min-w-0 flex-1 truncate">{item.name}</span>
                <span className="font-mono text-[10.5px] text-ink-3">{item.evidenceCount}</span>
              </DropdownMenu.Item>
            ))}
            <DropdownMenu.Separator className="my-1 h-px bg-line" />
            <DropdownMenu.Item
              className="flex cursor-default items-center gap-2 rounded-[7px] px-2 py-1.5 text-[12.5px] text-ink-2 outline-none data-[highlighted]:bg-surface-3"
              onSelect={() => {
                setName("");
                setMode("create");
              }}
            >
              <Plus className="h-3.5 w-3.5" />
              New workspace
            </DropdownMenu.Item>
            <DropdownMenu.Item
              className="flex cursor-default items-center gap-2 rounded-[7px] px-2 py-1.5 text-[12.5px] text-ink-2 outline-none data-[highlighted]:bg-surface-3"
              onSelect={() => {
                setName(workspace.name);
                setMode("rename");
              }}
            >
              <Pencil className="h-3.5 w-3.5" />
              Rename workspace
            </DropdownMenu.Item>
            <DropdownMenu.Item
              disabled={workspace.isDefault}
              className="flex cursor-default items-center gap-2 rounded-[7px] px-2 py-1.5 text-[12.5px] text-danger outline-none data-[disabled]:opacity-40 data-[highlighted]:bg-danger/10"
              onSelect={() => setMode("delete")}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete workspace
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      <Dialog open={mode !== null} onOpenChange={(open) => !open && close()}>
        <DialogContent className="max-w-md p-5">
          {mode === "delete" ? (
            <>
              <DialogTitle className="text-[15px] font-semibold">Delete workspace?</DialogTitle>
              <DialogDescription className="mt-1 text-[12px] leading-relaxed text-ink-2">
                <span className="font-medium text-ink">{workspace.name}</span> will be removed. Its evidence,
                reports and audit entries move to the default workspace. The original files are retained.
              </DialogDescription>
              <div className="mt-4 flex justify-end gap-2">
                <Button variant="secondary" size="sm" onClick={close} disabled={busy}>
                  Cancel
                </Button>
                <Button variant="danger" size="sm" onClick={confirmDelete} disabled={busy}>
                  <Trash2 className="h-3.5 w-3.5" /> {busy ? "Deleting…" : "Delete"}
                </Button>
              </div>
            </>
          ) : (
            <>
              <DialogTitle className="text-[15px] font-semibold">
                {mode === "create" ? "New workspace" : "Rename workspace"}
              </DialogTitle>
              <DialogDescription className="mt-1 text-[12px] leading-relaxed text-ink-2">
                Evidence, people, timeline, reports and audit entries are kept separate per workspace.
              </DialogDescription>
              <Input
                autoFocus
                className="mt-3"
                value={name}
                maxLength={160}
                placeholder="Workspace name"
                onChange={(event) => setName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void submit();
                }}
              />
              <div className="mt-4 flex justify-end gap-2">
                <Button variant="secondary" size="sm" onClick={close} disabled={busy}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" onClick={submit} disabled={busy || !name.trim()}>
                  {busy ? "Saving…" : mode === "create" ? "Create" : "Save"}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

function NavItem({
  item,
  active,
  onNavigate,
  badge,
  dot,
}: {
  item: { id: View; label: string; icon: typeof LayoutGrid };
  active: boolean;
  onNavigate: (id: View) => void;
  badge?: number;
  dot?: boolean;
}) {
  return (
    <li>
      <button
        onClick={() => onNavigate(item.id)}
        aria-current={active ? "page" : undefined}
        className={cn(
          "group relative flex h-[35px] w-full items-center gap-2.5 rounded-[7px] px-2.5 text-[12.5px] transition-colors duration-150",
          active
            ? "bg-accent-soft font-medium text-accent"
            : "text-ink-2 hover:bg-surface-2 hover:text-ink",
        )}
      >
        {active && (
          <span className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full bg-accent" />
        )}
        <item.icon
          className={cn("h-4 w-4 shrink-0", active ? "text-accent" : "text-ink-3 group-hover:text-ink-2")}
          strokeWidth={1.8}
        />
        <span className="flex-1 truncate text-left">{item.label}</span>
        {badge !== undefined && badge > 0 && (
          <span className="rounded-[4px] bg-warning/12 px-1 py-0.5 font-mono text-[9.5px] font-medium leading-none text-warning">
            {badge}
          </span>
        )}
        {dot && <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-label="New insights" />}
      </button>
    </li>
  );
}

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { view, navigate, evidence, theme, workspace } = useApp();
  const vaultAttention = evidence.filter((e) => e.status === "review" || e.status === "failed").length;

  const go = (id: View) => {
    navigate(id);
    onNavigate?.();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="px-4 pb-4 pt-5">
        <Brand />
      </div>
      <div className="px-3 pb-4">
        <WorkspaceSwitch />
      </div>

      <nav className="flex-1 overflow-y-auto px-2.5 pb-2" aria-label="Primary">
        <p className="px-2 pb-1.5 pt-1 text-[10.5px] font-medium text-ink-3">Investigation</p>
        <ul className="space-y-[2px]">
          {navigation.map((item) => (
            <NavItem
              key={item.id}
              item={item}
              active={view === item.id}
              onNavigate={go}
              badge={item.id === "vault" ? vaultAttention : undefined}
              dot={item.id === "assistant"}
            />
          ))}
        </ul>

        <div className="mx-2.5 my-3.5 h-px bg-line" />

        <p className="px-2 pb-1.5 text-[10.5px] font-medium text-ink-3">Governance</p>
        <ul className="space-y-[2px]">
          {utilityNav.map((item) => (
            <NavItem key={item.id} item={item} active={view === item.id} onNavigate={go} />
          ))}
        </ul>
      </nav>

      <div className="mt-auto border-t border-line px-3 py-3">
        <div className="px-1 pb-2.5">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 text-[10.5px] text-ink-2">
              <ShieldCheck className="h-3 w-3 text-success" strokeWidth={1.9} />
              Custody ledger
            </span>
            <span className="font-mono text-[9.5px] text-success">sealed</span>
          </div>
          <p className="mt-1 font-mono text-[9.5px] leading-relaxed text-ink-3">
            sha-256 · {evidence.filter((item) => item.integrity === "verified").length}/{evidence.length} verified
          </p>
          <p className="mt-1 text-[9.5px] text-ink-3">
            {theme === "dark" ? "Dark" : "Light"} appearance · {workspace.caseId}
          </p>
        </div>

        <button
          onClick={() => go("settings")}
          className="flex w-full items-center gap-2.5 rounded-[8px] border-t border-line px-1.5 pb-1 pt-2.5 text-left transition-colors hover:bg-surface-2"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent font-mono text-[9.5px] font-medium text-on-accent">
            {workspace.analystInitials}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[11.5px] font-medium leading-tight">{workspace.analyst}</span>
            <span className="mt-0.5 block truncate text-[10px] leading-tight text-ink-3">
              {workspace.analystRole}
            </span>
          </span>
          <Settings className="h-3.5 w-3.5 text-ink-3" />
        </button>
      </div>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden w-[238px] shrink-0 border-r border-line bg-surface lg:block print:hidden">
      <div className="sticky top-0 h-dvh">
        <SidebarContent />
      </div>
    </aside>
  );
}
