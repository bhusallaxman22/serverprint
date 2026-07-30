import { NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth/guards";
import { getPrinterStatusSnapshot } from "@/lib/services/printer-status";

export async function GET() {
  const user = await getCurrentUser();
  if (!user) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }
  const snapshot = await getPrinterStatusSnapshot();
  return NextResponse.json({
    printer_name: snapshot.printerName,
    health: snapshot.health,
    queue_depth: snapshot.queueDepth,
    toner_percent: snapshot.tonerPercent,
    paper_percent: snapshot.paperPercent,
    status_message: snapshot.statusMessage,
    unavailable_reason: snapshot.unavailableReason,
    checked_at: snapshot.checkedAt,
  });
}
