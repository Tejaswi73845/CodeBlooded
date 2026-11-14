import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  Bell,
  ChevronRight,
  CircleCheck,
  Lightbulb,
  LogOut,
  Menu,
  Moon,
  Search,
  Settings,
  Settings2,
  ShieldAlert,
  Sun,
  UserRound,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { SidebarContent } from "./sidebar";
import { useApp, type View } from "@/store/app-store";
import { workspace } from "@/data/mock";
import { cn } from "@/lib/utils";
import { timeAgo } from "@/lib/format";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

const titles: Record<View, string> = {
  overview: "Overview",
  vault: "Evidence Vault",
  timeline: "Incident Timeline",
  people: "People & Connections",
  assistant: "AI Assistant",
  reports: "Reports",
  audit: "Audit Logs",
  settings: "Settings",
};

const notificationIcon = {
  insight: Lightbulb,
  processing: CircleCheck,
  integrity: ShieldAlert,
  system: Settings2,
};

function NotificationsPanel({ onClose }: { onClose: () => void }) {
  const { notifications, markAllRead, markRead, unreadCount } = useApp();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <button className="fixed inset-0 z-40 cursor-default" aria-label="Close notifications" onClick={onClose} />
      <div
        ref={ref}
        role="dialog"
        aria-label="Notifications"
        className="absolute right-0 top-[calc(100%+8px)] z-50 w-[344px] overflow-hidden rounded-[14px] border border-line bg-surface shadow-pop data-[state=open]:animate-scale-in"
      >
        <div className="flex items-center justify-between border-b border-line px-3.5 py-2.5">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-semibold">Notifications</span>
            {unreadCount > 0 && (
              <span className="rounded-full bg-accent-soft px-1.5 text-[10.5px] font-semibold text-accent">
                {unreadCount}
              </span>
            )}
          </div>
          <button
            onClick={markAllRead}
            className="text-[11.5px] font-medium text-accent hover:underline"
          >
            Mark all read
          </button>
        </div>
        <div className="max-h-[380px] overflow-y-auto">
          {notifications.length === 0 && (
            <p className="px-4 py-8 text-center text-[12px] text-ink-3">You're all caught up.</p>
          )}
          {notifications.map((n) => {
            const Icon = notificationIcon[n.kind];
            return (
              <button
                key={n.id}
                onClick={() => markRead(n.id)}
                className={cn(
                  "flex w-full gap-2.5 border-b border-line px-3.5 py-3 text-left transition-colors last:border-0 hover:bg-surface-2",
                  !n.read && "bg-accent-soft/30",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                    n.kind === "integrity"
                      ? "bg-danger/10 text-danger"
                      : n.kind === "insight"
                        ? "bg-warning/12 text-warning"
                        : "bg-accent-soft text-accent",
                  )}
                >
                  <Icon className="h-3 w-3" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5">
                    <span className={cn("truncate text-[12px]", n.read ? "font-medium text-ink-2" : "font-semibold")}>
                      {n.title}
                    </span>
                    {!n.read && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />}
                  </span>
                  <span className="mt-0.5 line-clamp-2 block text-[11.5px] leading-snug text-ink-2">
                    {n.body}
                  </span>
                  <span className="mt-1 block text-[10.5px] text-ink-3">{timeAgo(n.at)}</span>
                </span>
              </button>
            );
          })}
        </div>
        <div className="border-t border-line px-3.5 py-2">
          <button
            onClick={onClose}
            className="w-full text-center text-[11.5px] font-medium text-ink-2 hover:text-ink"
          >
            Close
          </button>
        </div>
      </div>
    </>
  );
}

export function Topbar() {
  const { view, navigate, theme, toggleTheme, unreadCount, setSearchOpen, toast } = useApp();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-surface/85 px-4 backdrop-blur-xl supports-[backdrop-filter]:bg-surface/70 sm:px-6 print:hidden">
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
            <Menu className="h-[18px] w-[18px]" />
          </Button>
        </SheetTrigger>
        <SheetContent
          title="Navigation"
          headerless
          className="max-w-[260px] bg-surface p-0"
        >
          <SidebarContent onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1.5 text-[12.5px]">
        <span className="hidden truncate text-ink-2 sm:inline">{workspace.name}</span>
        <ChevronRight className="hidden h-3 w-3 shrink-0 text-ink-3 sm:inline" />
        <span className="truncate font-medium">{titles[view]}</span>
      </nav>

      <div className="ml-auto flex items-center gap-0.5 sm:gap-1">
        <button
          onClick={() => setSearchOpen(true)}
          className="group hidden h-8 items-center gap-2 rounded-lg border border-line bg-surface-2 px-2.5 text-ink-3 transition-colors hover:border-line-strong hover:text-ink-2 sm:flex"
          aria-label="Search workspace"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="w-[116px] text-left text-[12px]">Search…</span>
          <kbd className="rounded border border-line bg-surface px-1 py-px font-sans text-[10px] text-ink-3">
            ⌘K
          </kbd>
        </button>
        <button
          onClick={() => setSearchOpen(true)}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-2 hover:bg-surface-3 sm:hidden"
          aria-label="Search workspace"
        >
          <Search className="h-4 w-4" />
        </button>

        <button
          onClick={toggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-2 transition-colors hover:bg-surface-3 hover:text-ink"
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </button>

        <div className="relative">
          <button
            onClick={() => setNotificationsOpen((o) => !o)}
            className={cn(
              "relative flex h-8 w-8 items-center justify-center rounded-lg text-ink-2 transition-colors hover:bg-surface-3 hover:text-ink",
              notificationsOpen && "bg-surface-3 text-ink",
            )}
            aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}
            aria-expanded={notificationsOpen}
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute right-[6px] top-[6px] h-[6px] w-[6px] rounded-full bg-danger ring-2 ring-surface" />
            )}
          </button>
          {notificationsOpen && <NotificationsPanel onClose={() => setNotificationsOpen(false)} />}
        </div>

        <div className="mx-1 hidden h-5 w-px bg-line sm:block" />

        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              className="flex h-8 items-center gap-2 rounded-full pl-0.5 pr-1 transition-colors hover:bg-surface-2"
              aria-label="Account menu"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-[10.5px] font-semibold text-white">
                {workspace.analystInitials}
              </span>
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content
              align="end"
              sideOffset={8}
              className="z-50 w-[230px] rounded-xl border border-line bg-surface p-1 shadow-pop data-[state=open]:animate-scale-in"
            >
              <div className="px-2.5 py-2">
                <p className="text-[12.5px] font-medium">{workspace.analyst}</p>
                <p className="text-[11px] text-ink-3">aarav.shah@kestrel.legal</p>
              </div>
              <DropdownMenu.Separator className="my-1 h-px bg-line" />
              <DropdownMenu.Item
                onSelect={() => toast("Profile", "Profile management is available in Settings.")}
                className="flex cursor-default items-center gap-2 rounded-lg px-2.5 py-1.5 text-[12.5px] outline-none data-[highlighted]:bg-surface-3"
              >
                <UserRound className="h-3.5 w-3.5 text-ink-3" /> Profile
              </DropdownMenu.Item>
              <DropdownMenu.Item
                onSelect={() => navigate("settings")}
                className="flex cursor-default items-center gap-2 rounded-lg px-2.5 py-1.5 text-[12.5px] outline-none data-[highlighted]:bg-surface-3"
              >
                <Settings className="h-3.5 w-3.5 text-ink-3" /> Settings
              </DropdownMenu.Item>
              <DropdownMenu.Item
                onSelect={() => setSearchOpen(true)}
                className="flex cursor-default items-center gap-2 rounded-lg px-2.5 py-1.5 text-[12.5px] outline-none data-[highlighted]:bg-surface-3"
              >
                <Search className="h-3.5 w-3.5 text-ink-3" /> Search
                <kbd className="ml-auto font-sans text-[10px] text-ink-3">⌘K</kbd>
              </DropdownMenu.Item>
              <DropdownMenu.Separator className="my-1 h-px bg-line" />
              <DropdownMenu.Item
                onSelect={() => toast("Signed out", "Demo session — sign-in is not enabled.", "default")}
                className="flex cursor-default items-center gap-2 rounded-lg px-2.5 py-1.5 text-[12.5px] text-danger outline-none data-[highlighted]:bg-danger/10"
              >
                <LogOut className="h-3.5 w-3.5" /> Sign out
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  );
}
