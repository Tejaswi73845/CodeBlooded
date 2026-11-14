import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { CommandPalette } from "@/components/layout/command-palette";
import { EvidenceDrawer } from "@/components/evidence/evidence-drawer";
import { ToastViewport } from "@/components/ui/toast";
import { useApp } from "@/store/app-store";
import { DashboardPage } from "@/pages/dashboard";
import { VaultPage } from "@/pages/vault";
import { TimelinePage } from "@/pages/timeline";
import { PeoplePage } from "@/pages/people";
import { AssistantPage } from "@/pages/assistant";
import { ReportsPage } from "@/pages/reports";
import { AuditPage } from "@/pages/audit";
import { SettingsPage } from "@/pages/settings";
import { AuthPage } from "@/pages/auth";

export default function App() {
  const { view, workspace, user, authReady } = useApp();

  if (!authReady) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg text-[12px] text-ink-3">
        Loading workspace…
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <AuthPage />
        <ToastViewport />
      </>
    );
  }

  const page = {
    overview: <DashboardPage />,
    vault: <VaultPage />,
    timeline: <TimelinePage />,
    people: <PeoplePage />,
    assistant: <AssistantPage />,
    reports: <ReportsPage />,
    audit: <AuditPage />,
    settings: <SettingsPage />,
  }[view];

  return (
    <div className="flex min-h-dvh bg-bg">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-5 sm:px-6 lg:px-8 print:p-0">
          <div key={view}>{page}</div>
        </main>
        <footer className="mx-auto hidden w-full max-w-[1440px] items-center justify-between gap-4 px-4 pb-4 text-[10px] text-ink-3 sm:px-6 lg:flex lg:px-8 print:hidden">
          <span>Veritas Evidence Intelligence · {workspace.name}</span>
          <span className="inline-flex items-center gap-3">
            <span>Case {workspace.caseId}</span>
            <span className="h-2.5 w-px bg-line" />
            <span>SHA-256 custody ledger</span>
          </span>
        </footer>
      </div>
      <EvidenceDrawer />
      <CommandPalette />
      <ToastViewport />
    </div>
  );
}
