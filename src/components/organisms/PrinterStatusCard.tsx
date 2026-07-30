import { Badge } from "@/components/atoms/Badge";
import type { PrinterStatusSnapshot } from "@/lib/services/printer-status";

export function PrinterStatusCard({ printer }: { printer: PrinterStatusSnapshot }) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-border bg-bg-elevated/60 px-3 py-2.5">
      <span
        className={`h-2.5 w-2.5 shrink-0 rounded-full animate-pulse-soft ${
          printer.health === "online"
            ? "bg-success"
            : printer.health === "warning"
              ? "bg-warning"
              : "bg-danger"
        }`}
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{printer.printerName}</p>
        <p className="truncate text-xs text-text-muted">
          {printer.statusMessage ?? printer.unavailableReason ?? "Status unknown"}
        </p>
      </div>
      <Badge tone={printer.health}>{printer.health}</Badge>
      {printer.queueDepth !== null ? (
        <span className="text-xs text-text-muted">Q {printer.queueDepth}</span>
      ) : null}
    </div>
  );
}
