import { useState } from "react";
import { Fingerprint, ShieldCheck, Waypoints } from "lucide-react";
import { useApp } from "@/store/app-store";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";

type Mode = "signin" | "signup";

const principles = [
  { icon: Fingerprint, label: "SHA-256 at intake", detail: "originals preserved before processing" },
  { icon: Waypoints, label: "Chained custody ledger", detail: "every access and export is recorded" },
  { icon: ShieldCheck, label: "Answers with sources", detail: "each claim returns to its evidence" },
];

export function AuthPage() {
  const { signIn, signUp } = useApp();
  const [mode, setMode] = useState<Mode>("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (busy) return;
    setBusy(true);
    const ok =
      mode === "signin"
        ? await signIn(email.trim(), password)
        : await signUp(name.trim(), email.trim(), password);
    setBusy(false);
    if (!ok) setPassword("");
  };

  const disabled =
    busy ||
    !email.trim() ||
    !password ||
    (mode === "signup" && !name.trim());

  return (
    <div className="min-h-dvh bg-bg lg:grid lg:grid-cols-[1.06fr_1fr]">
      <aside className="relative hidden overflow-hidden border-r border-[#2a2f27] bg-[#131612] p-10 text-[#eceade] lg:flex lg:flex-col lg:justify-between xl:p-14">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.16]"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(236,234,222,0.18) 1px, transparent 1px)",
            backgroundSize: "72px 100%",
          }}
          aria-hidden
        />
        <div className="relative flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#7a2e36] font-serif text-[18px] leading-none text-[#fdf7f2]">
            V
          </span>
          <div>
            <p className="font-serif text-[20px] font-medium leading-none tracking-[-0.015em]">Veritas</p>
            <p className="mt-1.5 font-mono text-[9px] text-[#8b927f]">evidence intelligence</p>
          </div>
        </div>

        <div className="relative max-w-[440px]">
          <p className="font-mono text-[9.5px] text-[#9aa18c]">case file · 2026</p>
          <h1 className="mt-4 font-serif text-[44px] font-normal leading-[1.02] tracking-[-0.025em] xl:text-[52px]">
            Evidence,
            <br />
            kept in order.
          </h1>
          <p className="mt-5 max-w-[360px] text-[12.5px] leading-relaxed text-[#b9bfae]">
            A working dossier for digital evidence: preserve the original, reconstruct the
            chronology, and keep every conclusion tied to its source.
          </p>
        </div>

        <ul className="relative space-y-3 border-t border-[#2d322a] pt-5">
          {principles.map((item) => (
            <li key={item.label} className="flex items-start gap-3">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-[5px] border border-[#363c31] text-[#a9b09d]">
                <item.icon className="h-3 w-3" strokeWidth={1.8} />
              </span>
              <span>
                <span className="block text-[11.5px] font-medium text-[#e4e2d5]">{item.label}</span>
                <span className="mt-0.5 block text-[10.5px] text-[#8b927f]">{item.detail}</span>
              </span>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex min-h-dvh items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-[360px]">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent font-serif text-[18px] leading-none text-on-accent">
              V
            </span>
            <div>
              <p className="font-serif text-[19px] font-medium leading-none tracking-[-0.015em]">Veritas</p>
              <p className="mt-1 text-[9.5px] text-ink-3">Evidence intelligence</p>
            </div>
          </div>

          <p className="font-mono text-[9.5px] text-ink-3">
            {mode === "signin" ? "workspace access" : "new analyst account"}
          </p>
          <h2 className="mt-2 font-serif text-[30px] font-normal leading-tight tracking-[-0.02em]">
            {mode === "signin" ? "Sign in" : "Create account"}
          </h2>
          <p className="mt-1.5 text-[12px] leading-relaxed text-ink-2">
            {mode === "signin"
              ? "Access your investigation workspace."
              : "Create an analyst account on this server."}
          </p>

          <form
            className="mt-6 space-y-3.5"
            onSubmit={(event) => {
              event.preventDefault();
              void submit();
            }}
          >
            {mode === "signup" && (
              <Field label="Name">
                <Input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  autoComplete="name"
                  placeholder="Analyst name"
                />
              </Field>
            )}
            <Field label="Email">
              <Input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                placeholder="you@example.com"
              />
            </Field>
            <Field label="Password" hint={mode === "signup" ? "At least 6 characters." : undefined}>
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                placeholder="••••••••"
              />
            </Field>
            <Button type="submit" variant="primary" size="lg" className="w-full" disabled={disabled}>
              {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <div className="mt-5 flex items-center justify-between text-[11.5px] text-ink-3">
            <span>{mode === "signin" ? "New here?" : "Already have an account?"}</span>
            <button
              type="button"
              onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
              className="font-medium text-accent hover:underline"
            >
              {mode === "signin" ? "Create account" : "Sign in"}
            </button>
          </div>

          <div className="mt-8 border-t border-line pt-4">
            <p className="flex items-start gap-1.5 text-[10.5px] leading-relaxed text-ink-3">
              <ShieldCheck className="mt-px h-3 w-3 shrink-0 text-success" />
              <span>
                Local demo account: <span className="font-mono text-ink-2">aarav.shah@kestrel.legal</span>
                {"  ·  "}
                <span className="font-mono text-ink-2">tracevault</span>
              </span>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
