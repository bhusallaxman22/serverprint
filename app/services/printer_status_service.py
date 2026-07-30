from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.security import now_utc
from app.services.cups_service import CUPSService


PrinterHealth = Literal["online", "warning", "offline", "unknown"]


@dataclass
class PrinterStatusSnapshot:
    printer_name: str
    health: PrinterHealth
    queue_depth: int | None
    toner_percent: int | None
    paper_percent: int | None
    status_message: str | None
    unavailable_reason: str | None
    checked_at: datetime


def get_printer_status_snapshot(cups: CUPSService) -> PrinterStatusSnapshot:
    reachable, reason = cups.check_printer_reachability()
    queue_depth: int | None = None
    health: PrinterHealth = "unknown"
    status_message: str | None = None
    unavailable_reason: str | None = reason
    if reachable:
        active_states = cups.fetch_job_states()
        if active_states is None:
            health = "unknown"
            status_message = "Printer telemetry unavailable."
            unavailable_reason = "Unable to fetch queue state from CUPS."
        else:
            queue_depth = len(active_states)
            health = "online" if queue_depth == 0 else "warning"
            status_message = (
                "Printer reachable." if queue_depth == 0 else "Printer has active queued jobs."
            )
            unavailable_reason = None
    else:
        health = "offline"
        status_message = "Printer telemetry unavailable."

    return PrinterStatusSnapshot(
        printer_name=cups.printer_name,
        health=health,
        queue_depth=queue_depth,
        toner_percent=None,
        paper_percent=None,
        status_message=status_message,
        unavailable_reason=unavailable_reason,
        checked_at=now_utc(),
    )
