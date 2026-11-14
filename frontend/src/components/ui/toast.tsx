import { AlertTriangle, CircleCheck, Info } from "lucide-react";
import { useApp } from "@/store/app-store";
import { cn } from "@/lib/utils";

export function ToastViewport() {
  const { toasts } = useApp();
  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[70] flex w-[342px] max-w-[calc(100vw-2rem)] flex-col gap-2 print:hidden">
      {toasts.map((t) => {
        const Icon = t.tone === "success" ? CircleCheck : t.tone === "danger" ? AlertTriangle : Info;
        return (
          <div
            key={t.id}
            role="status"
            className="pointer-events-auto flex items-start gap-2.5 rounded-[10px] border border-line-strong/60 bg-surface/97 px-3 py-2.5 shadow-pop backdrop-blur-xl animate-rise"
          >
            <Icon
              className={cn(
                "mt-px h-4 w-4 shrink-0",
                t.tone === "success" ? "text-success" : t.tone === "danger" ? "text-danger" : "text-accent",
              )}
            />
            <div className="min-w-0">
              <p className="text-[12.5px] font-medium leading-snug">{t.title}</p>
              {t.description && (
                <p className="mt-0.5 text-[11.5px] leading-snug text-ink-2">{t.description}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
