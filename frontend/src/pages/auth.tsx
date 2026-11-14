import { useState } from "react";
import { ShieldCheck, Sparkles } from "lucide-react";
import { useApp } from "@/store/app-store";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";

type Mode = "signin" | "signup";

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
    <div className="flex min-h-dvh items-center justify-center bg-bg px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink text-surface">
            <Sparkles className="h-4 w-4" />
          </span>
          <div>
            <p className="text-[15px] font-semibold tracking-[-0.02em]">Veritas</p>
            <p className="text-[10px] font-medium uppercase tracking-[0.09em] text-ink-3">
              Evidence Intelligence
            </p>
          </div>
        </div>

        <div className="rounded-card border border-line bg-surface p-5 shadow-card">
          <h1 className="text-[17px] font-semibold tracking-[-0.02em]">
            {mode === "signin" ? "Sign in" : "Create account"}
          </h1>
          <p className="mt-1 text-[12px] leading-relaxed text-ink-2">
            {mode === "signin"
              ? "Access your investigation workspace."
              : "Create an analyst account on this server."}
          </p>

          <form
            className="mt-4 space-y-3"
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
            <Button type="submit" variant="primary" className="w-full" disabled={disabled}>
              {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <div className="mt-4 flex items-center justify-between text-[11.5px] text-ink-3">
            <span>{mode === "signin" ? "New here?" : "Already have an account?"}</span>
            <button
              type="button"
              onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
              className="font-medium text-accent hover:underline"
            >
              {mode === "signin" ? "Create account" : "Sign in"}
            </button>
          </div>
        </div>

        <p className="mt-4 flex items-start gap-1.5 text-[10.5px] leading-relaxed text-ink-3">
          <ShieldCheck className="mt-px h-3 w-3 shrink-0 text-success" />
          Default local account: <span className="font-mono">aarav.shah@kestrel.legal</span> ·{" "}
          <span className="font-mono">tracevault</span>
        </p>
      </div>
    </div>
  );
}
