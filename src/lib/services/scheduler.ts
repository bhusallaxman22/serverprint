import { config } from "@/lib/config";
import { prisma } from "@/lib/db/prisma";
import { cleanupStaleJobsAndFiles } from "@/lib/services/cleanup";
import { CUPSService } from "@/lib/services/cups";
import { syncQueuedJobsFromCups } from "@/lib/services/jobs";

let started = false;

export function startBackgroundScheduler(): void {
  if (started || !config.runScheduler) return;
  started = true;

  const cups = new CUPSService(config.cupsServer, config.printerName);
  const pollMs = Math.max(5, config.printStatusPollSeconds) * 1000;

  const sync = async () => {
    try {
      await syncQueuedJobsFromCups(prisma, cups);
    } catch (err) {
      console.error("CUPS sync failed", err);
    }
  };

  const cleanup = async () => {
    try {
      await cleanupStaleJobsAndFiles(
        prisma,
        config.uploadsRoot,
        config.failedFileRetentionHours,
        config.pendingFileRetentionDays,
      );
    } catch (err) {
      console.error("Cleanup failed", err);
    }
  };

  void sync();
  setInterval(() => void sync(), pollMs);
  setInterval(() => void cleanup(), 60 * 60 * 1000);
}
