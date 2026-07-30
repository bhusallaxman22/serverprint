import { config } from "@/lib/config";
import { CUPSService } from "@/lib/services/cups";

export type PrinterHealth = "online" | "warning" | "offline" | "unknown";

export type PrinterStatusSnapshot = {
  printerName: string;
  health: PrinterHealth;
  queueDepth: number | null;
  tonerPercent: number | null;
  paperPercent: number | null;
  statusMessage: string | null;
  unavailableReason: string | null;
  checkedAt: string;
};

export async function getPrinterStatusSnapshot(
  cups = new CUPSService(config.cupsServer, config.printerName),
): Promise<PrinterStatusSnapshot> {
  const { reachable, reason } = await cups.checkPrinterReachability();
  let queueDepth: number | null = null;
  let health: PrinterHealth = "unknown";
  let statusMessage: string | null = null;
  let unavailableReason: string | null = reason;

  if (reachable) {
    const activeStates = await cups.fetchJobStates();
    if (activeStates === null) {
      health = "unknown";
      statusMessage = "Printer telemetry unavailable.";
      unavailableReason = "Unable to fetch queue state from CUPS.";
    } else {
      queueDepth = activeStates.length;
      health = queueDepth === 0 ? "online" : "warning";
      statusMessage =
        queueDepth === 0
          ? "Printer reachable."
          : "Printer has active queued jobs.";
      unavailableReason = null;
    }
  } else {
    health = "offline";
    statusMessage = "Printer telemetry unavailable.";
  }

  return {
    printerName: cups.printerName,
    health,
    queueDepth,
    tonerPercent: null,
    paperPercent: null,
    statusMessage,
    unavailableReason,
    checkedAt: new Date().toISOString(),
  };
}
