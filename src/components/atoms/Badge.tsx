const tones: Record<string, string> = {
  pending: "bg-warning/15 text-warning",
  approved: "bg-accent/15 text-accent",
  queued: "bg-accent/15 text-accent",
  printing: "bg-accent/20 text-accent",
  completed: "bg-success/15 text-success",
  failed: "bg-danger/15 text-danger",
  rejected: "bg-danger/15 text-danger",
  cancelled: "bg-text-muted/15 text-text-muted",
  admin: "bg-accent/15 text-accent",
  user: "bg-white/5 text-text-muted",
  online: "bg-success/15 text-success",
  warning: "bg-warning/15 text-warning",
  offline: "bg-danger/15 text-danger",
  unknown: "bg-text-muted/15 text-text-muted",
};

export function Badge({
  children,
  tone = "unknown",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide ${
        tones[tone] ?? tones.unknown
      }`}
    >
      {children}
    </span>
  );
}
