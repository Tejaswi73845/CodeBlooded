import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export const SheetClose = DialogPrimitive.Close;
export const SheetTitle = DialogPrimitive.Title;
export const SheetDescription = DialogPrimitive.Description;

export function SheetContent({
  className,
  children,
  title,
  description,
  headerless,
  ...props
}: ComponentProps<typeof DialogPrimitive.Content> & {
  title: ReactNode;
  description?: string;
  headerless?: boolean;
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/25 backdrop-blur-[1px] data-[state=open]:animate-fade-in dark:bg-black/55" />
      <DialogPrimitive.Content
        tabIndex={-1}
        onOpenAutoFocus={(e) => {
          e.preventDefault();
          (e.currentTarget as HTMLElement).focus();
        }}
        className={cn(
          "fixed inset-y-0 right-0 z-50 flex w-full max-w-[480px] flex-col border-l border-line bg-surface shadow-pop outline-none",
          "data-[state=closed]:translate-x-full data-[state=open]:translate-x-0 transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]",
          className,
        )}
        {...props}
      >
        <DialogPrimitive.Title className="sr-only">{title}</DialogPrimitive.Title>
        <DialogPrimitive.Description className={description ? "sr-only" : "sr-only"}>
          {description ?? "Panel"}
        </DialogPrimitive.Description>
        <div className={headerless ? "hidden" : "flex items-start justify-between gap-4 border-b border-line px-5 py-4"}>
          <div className="min-w-0">
            <span className="block truncate text-[15px] font-semibold tracking-[-0.01em]">{title}</span>
            {description && (
              <span className="mt-0.5 block truncate text-[12px] text-ink-2">{description}</span>
            )}
          </div>
          <DialogPrimitive.Close
            aria-label="Close panel"
            className="-mr-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-ink-3 transition-colors hover:bg-surface-3 hover:text-ink"
          >
            <X className="h-4 w-4" />
          </DialogPrimitive.Close>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
