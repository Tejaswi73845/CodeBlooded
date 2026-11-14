import {
  ArrowLeft,
  Check,
  Cloud,
  Database,
  Fingerprint,
  KeyRound,
  Loader2,
  Moon,
  Palette,
  Save,
  ShieldCheck,
  Sun,
  UserRound,
  Workflow,
} from "lucide-react";
import { useState } from "react";
import { useApp } from "@/store/app-store";
import { workspace } from "@/data/mock";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { Segmented, Switch } from "@/components/ui/segmented";
import { cn } from "@/lib/utils";

export function SettingsPage() {
  const { theme, toggleTheme, toast, navigate } = useApp();
  const [name, setName] = useState(workspace.analyst);
  const [email, setEmail] = useState("aarav.shah@kestrel.legal");
  const [defaultView, setDefaultView] = useState("overview");
  const [compact, setCompact] = useState(false);
  const [autoVerify, setAutoVerify] = useState(true);
  const [notifyInsights, setNotifyInsights] = useState(true);
  const [notifyProcessing, setNotifyProcessing] = useState(true);
  const [notifyDigest, setNotifyDigest] = useState(false);
  const [twoFactor, setTwoFactor] = useState(true);
  const [redact, setRedact] = useState(true);
  const [sessionTimeout, setSessionTimeout] = useState("30");
  const [style, setStyle] = useState<"concise" | "balanced" | "detailed">("balanced");
  const [apiUrl, setApiUrl] = useState("https://api.veritas.local/v1");
  const [testing, setTesting] = useState(false);
  const [connected, setConnected] = useState(true);

  const save = (section: string) => toast("Preferences saved", `${section} updated for this workspace.`, "success");

  const testConnection = () => {
    setTesting(true);
    setConnected(false);
    window.setTimeout(() => {
      setTesting(false);
      setConnected(true);
      toast("FastAPI reachable", "GET /health returned 200 · schema v1.4.", "success");
    }, 1100);
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Settings"
        description="Workspace appearance, investigation defaults, security posture and backend integration."
        actions={
          <Button variant="secondary" onClick={() => navigate("overview")}>
            <ArrowLeft className="h-3.5 w-3.5" /> Back to case
          </Button>
        }
      />

      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Palette className="h-4 w-4 text-ink-3" />
              <CardTitle>Appearance</CardTitle>
            </div>
            <Badge tone="neutral">{theme === "light" ? "Light" : "Dark"} mode</Badge>
          </CardHeader>
          <CardContent className="mt-3">
            <div className="grid gap-2.5 sm:grid-cols-2">
              <button
                onClick={() => theme === "dark" && toggleTheme()}
                aria-pressed={theme === "light"}
                className={cn(
                  "rounded-xl border p-3 text-left transition-colors",
                  theme === "light" ? "border-accent ring-2 ring-accent/15" : "border-line hover:bg-surface-2",
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#F5F5F7] text-[#1D1D1F]">
                    <Sun className="h-3.5 w-3.5" />
                  </span>
                  <span className="text-[12px] font-medium">Light</span>
                  {theme === "light" && <Check className="ml-auto h-3.5 w-3.5 text-accent" />}
                </div>
                <div className="mt-2.5 rounded-lg border border-[#E5E5EA] bg-[#F5F5F7] p-2">
                  <div className="flex gap-1.5">
                    <div className="h-10 w-6 rounded bg-white" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-3 w-2/3 rounded bg-white" />
                      <div className="h-2 w-full rounded bg-[#E5E5EA]" />
                      <div className="h-2 w-4/5 rounded bg-[#E5E5EA]" />
                    </div>
                  </div>
                </div>
                <p className="mt-2 text-[10.5px] text-ink-3">Default appearance for review work.</p>
              </button>

              <button
                onClick={() => theme === "light" && toggleTheme()}
                aria-pressed={theme === "dark"}
                className={cn(
                  "rounded-xl border p-3 text-left transition-colors",
                  theme === "dark" ? "border-accent ring-2 ring-accent/15" : "border-line hover:bg-surface-2",
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#1C1C1E] text-[#F5F5F7]">
                    <Moon className="h-3.5 w-3.5" />
                  </span>
                  <span className="text-[12px] font-medium">Dark</span>
                  {theme === "dark" && <Check className="ml-auto h-3.5 w-3.5 text-accent" />}
                </div>
                <div className="mt-2.5 rounded-lg border border-[#2E2E31] bg-[#0A0A0B] p-2">
                  <div className="flex gap-1.5">
                    <div className="h-10 w-6 rounded bg-[#1C1C1E]" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-3 w-2/3 rounded bg-[#1C1C1E]" />
                      <div className="h-2 w-full rounded bg-[#2E2E31]" />
                      <div className="h-2 w-4/5 rounded bg-[#2E2E31]" />
                    </div>
                  </div>
                </div>
                <p className="mt-2 text-[10.5px] text-ink-3">Lower luminance for long review sessions.</p>
              </button>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3 border-t border-line pt-3">
              <div>
                <p className="text-[12px] font-medium">Compact evidence tables</p>
                <p className="text-[10.5px] text-ink-3">Tighter rows in the vault and audit log.</p>
              </div>
              <Switch checked={compact} onChange={(v) => { setCompact(v); save("Table density"); }} label="Compact tables" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <UserRound className="h-4 w-4 text-ink-3" />
              <CardTitle>Profile</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="mt-3 space-y-3">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-accent text-[13px] font-semibold text-white">
                {workspace.analystInitials}
              </span>
              <div>
                <p className="text-[12px] font-medium">{name}</p>
                <p className="text-[10.5px] text-ink-3">{workspace.analystRole} · Kestrel Legal</p>
              </div>
              <Button variant="secondary" size="sm" className="ml-auto" onClick={() => toast("Photo upload", "Avatars are managed by your identity provider.")}>
                Change
              </Button>
            </div>
            <Field label="Full name">
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label="Email">
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <Button variant="primary" size="sm" onClick={() => save("Profile")}>
              <Save className="h-3.5 w-3.5" /> Save profile
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Workflow className="h-4 w-4 text-ink-3" />
              <CardTitle>Investigation defaults</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="mt-3 space-y-3">
            <Field label="Default view" hint="Used when the workspace opens.">
              <select
                value={defaultView}
                onChange={(e) => setDefaultView(e.target.value)}
                className="h-9 w-full rounded-[10px] border border-line bg-surface px-2.5 text-[13px] outline-none"
              >
                <option value="overview">Overview</option>
                <option value="vault">Evidence Vault</option>
                <option value="timeline">Incident Timeline</option>
                <option value="people">People & Connections</option>
                <option value="assistant">AI Assistant</option>
              </select>
            </Field>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[12px] font-medium">Hash on intake</p>
                <p className="text-[10.5px] text-ink-3">Compute SHA-256 before any processing.</p>
              </div>
              <Switch checked={autoVerify} onChange={setAutoVerify} label="Hash on intake" />
            </div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[12px] font-medium">Notify on new insights</p>
                <p className="text-[10.5px] text-ink-3">In-app notification when confidence ≥ 80%.</p>
              </div>
              <Switch checked={notifyInsights} onChange={setNotifyInsights} label="Notify on insights" />
            </div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[12px] font-medium">Processing updates</p>
                <p className="text-[10.5px] text-ink-3">Notify when a file becomes searchable.</p>
              </div>
              <Switch checked={notifyProcessing} onChange={setNotifyProcessing} label="Notify on processing" />
            </div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[12px] font-medium">Daily digest</p>
                <p className="text-[10.5px] text-ink-3">A morning summary of case activity.</p>
              </div>
              <Switch checked={notifyDigest} onChange={setNotifyDigest} label="Daily digest" />
            </div>
            <Button variant="primary" size="sm" onClick={() => save("Investigation defaults")}>
              <Save className="h-3.5 w-3.5" /> Save defaults
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-ink-3" />
              <CardTitle>Security</CardTitle>
            </div>
            <Badge tone="success" dot>
              Hardened
            </Badge>
          </CardHeader>
          <CardContent className="mt-3 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[12px] font-medium">Two-factor authentication</p>
                <p className="text-[10.5px] text-ink-3">Required for evidence export and deletion.</p>
              </div>
              <Switch checked={twoFactor} onChange={setTwoFactor} label="Two-factor authentication" />
            </div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[12px] font-medium">Redact PII in exports</p>
                <p className="text-[10.5px] text-ink-3">Masks phone numbers and email addresses.</p>
              </div>
              <Switch checked={redact} onChange={setRedact} label="Redact PII in exports" />
            </div>
            <Field label="Session timeout">
              <select
                value={sessionTimeout}
                onChange={(e) => setSessionTimeout(e.target.value)}
                className="h-9 w-full rounded-[10px] border border-line bg-surface px-2.5 text-[13px] outline-none"
              >
                <option value="15">15 minutes</option>
                <option value="30">30 minutes</option>
                <option value="60">1 hour</option>
                <option value="480">8 hours</option>
              </select>
            </Field>
            <div className="rounded-lg border border-line bg-surface-2 p-2.5">
              <p className="flex items-center gap-1.5 font-mono text-[10px] text-ink-2">
                <Fingerprint className="h-3 w-3 text-ink-3" /> custody key · rotated 6 Nov 2026
              </p>
              <p className="mt-1 break-all font-mono text-[9.5px] text-ink-3">
                ed25519:4a7c19d7f04b2e6a1c9d38f57b0e42c6d9a1f83e7b52c04d8a6f91
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Cloud className="h-4 w-4 text-ink-3" />
              <CardTitle>API integration</CardTitle>
            </div>
            <Badge tone={connected ? "success" : "warning"} dot>
              {connected ? "Connected" : "Mock mode"}
            </Badge>
          </CardHeader>
          <CardContent className="mt-3 space-y-3">
            <Field label="FastAPI base URL" hint="All evidence, graph and chat calls route through this endpoint.">
              <Input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} className="font-mono text-[11.5px]" />
            </Field>
            <Field label="Workspace key">
              <Input value="sk_live_••••••••••••4f2a" readOnly className="font-mono text-[11.5px] text-ink-2" />
            </Field>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={testConnection} disabled={testing}>
                {testing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Database className="h-3.5 w-3.5" />}
                {testing ? "Testing…" : "Test connection"}
              </Button>
              <span className="text-[10.5px] text-ink-3">Mock data is served locally until the endpoint is live.</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <SparklesIcon />
              <CardTitle>Assistant behaviour</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="mt-3 space-y-3">
            <Field label="Response style" hint="Citations are always included and cannot be disabled.">
              <Segmented
                value={style}
                onChange={setStyle}
                options={[
                  { value: "concise", label: "Concise" },
                  { value: "balanced", label: "Balanced" },
                  { value: "detailed", label: "Detailed" },
                ]}
              />
            </Field>
            <div className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface-2 px-3 py-2">
              <div className="flex items-center gap-2">
                <KeyRound className="h-3.5 w-3.5 text-ink-3" />
                <div>
                  <p className="text-[11.5px] font-medium">Evidence-only answers</p>
                  <p className="text-[10px] text-ink-3">Refuse when a claim has no source.</p>
                </div>
              </div>
              <Badge tone="success">Enforced</Badge>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2">
              <div>
                <p className="text-[11.5px] font-medium">Save assistant transcripts</p>
                <p className="text-[10px] text-ink-3">Retained with the case audit log for 7 years.</p>
              </div>
              <Switch checked label="Save assistant transcripts" onChange={() => toast("Policy locked", "Transcript retention is set by the firm's policy.", "default")} />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-3 rounded-card border border-line bg-surface px-4 py-3 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[12px] font-medium">Workspace retention</p>
            <p className="mt-0.5 text-[10.5px] text-ink-3">
              Evidence and audit entries are retained for 7 years, then sealed and archived.
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => toast("Data policy", "An export of the current policy has been prepared.", "success")}>
            Download policy
          </Button>
        </div>
      </div>
    </div>
  );
}

function SparklesIcon() {
  return (
    <span className="flex h-4 w-4 items-center justify-center text-ink-3">
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" strokeLinecap="round" />
      </svg>
    </span>
  );
}
