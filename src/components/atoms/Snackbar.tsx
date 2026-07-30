"use client";

export type SnackbarTone = "success" | "error" | "info";

export type SnackbarItem = {
  id: string;
  message: string;
  tone: SnackbarTone;
};

const toneStyles: Record<SnackbarTone, string> = {
  success: "border-success/40 bg-success/15 text-success",
  error: "border-danger/40 bg-danger/15 text-danger",
  info: "border-accent/40 bg-accent/15 text-accent",
};

export function Snackbar({
  item,
  onDismiss,
}: {
  item: SnackbarItem;
  onDismiss: (id: string) => void;
}) {
  return (
    <div
      role="status"
      className={`pointer-events-auto flex max-w-sm items-start gap-3 rounded-md border px-3.5 py-3 text-sm shadow-lg backdrop-blur animate-fade-up ${toneStyles[item.tone]}`}
    >
      <p className="flex-1 leading-snug text-text">{item.message}</p>
      <button
        type="button"
        onClick={() => onDismiss(item.id)}
        className="shrink-0 rounded px-1.5 py-0.5 text-xs text-text-muted hover:bg-white/10 hover:text-text"
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  );
}
