import { config as loadEnv } from "dotenv";
loadEnv();

import { config } from "../src/lib/config";
import { prisma } from "../src/lib/db/prisma";
import { bootstrapAdmin } from "../src/lib/services/bootstrap";
import { cleanupStaleJobsAndFiles } from "../src/lib/services/cleanup";
import { CUPSService } from "../src/lib/services/cups";
import { syncQueuedJobsFromCups } from "../src/lib/services/jobs";
import fs from "node:fs";

async function main() {
  fs.mkdirSync(config.uploadsRoot, { recursive: true });
  fs.mkdirSync(config.tmpRoot, { recursive: true });
  await bootstrapAdmin();

  const cups = new CUPSService(config.cupsServer, config.printerName);
  const pollMs = Math.max(5, config.printStatusPollSeconds) * 1000;

  console.log(
    `PrintDrop worker started (poll=${config.printStatusPollSeconds}s, printer=${config.printerName})`,
  );

  const sync = async () => {
    try {
      const n = await syncQueuedJobsFromCups(prisma, cups);
      if (n > 0) console.log(`Synced ${n} job status update(s)`);
    } catch (err) {
      console.error("CUPS sync failed", err);
    }
  };

  const cleanup = async () => {
    try {
      const n = await cleanupStaleJobsAndFiles(
        prisma,
        config.uploadsRoot,
        config.failedFileRetentionHours,
        config.pendingFileRetentionDays,
      );
      if (n > 0) console.log(`Cleaned ${n} stale job(s)`);
    } catch (err) {
      console.error("Cleanup failed", err);
    }
  };

  await sync();
  setInterval(() => void sync(), pollMs);
  setInterval(() => void cleanup(), 60 * 60 * 1000);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
