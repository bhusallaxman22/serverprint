import { PrintJobStatus, type Prisma, type PrismaClient } from "@prisma/client";
import fs from "node:fs/promises";
import path from "node:path";

type DbClient = PrismaClient | Prisma.TransactionClient;

export async function cleanupStaleJobsAndFiles(
  db: DbClient,
  uploadsRoot: string,
  failedRetentionHours: number,
  pendingRetentionDays: number,
): Promise<number> {
  const now = new Date();
  const failedCutoff = new Date(now.getTime() - failedRetentionHours * 3600_000);
  const pendingCutoff = new Date(now.getTime() - pendingRetentionDays * 86_400_000);

  const jobs = await db.printJob.findMany({
    where: {
      OR: [
        { status: PrintJobStatus.failed, updatedAt: { lt: failedCutoff } },
        { status: PrintJobStatus.pending, submittedAt: { lt: pendingCutoff } },
      ],
    },
  });

  for (const job of jobs) {
    const safePath = path.join(uploadsRoot, job.storedFilename);
    try {
      await fs.unlink(safePath);
    } catch {
      // ignore missing files
    }
  }

  if (jobs.length === 0) return 0;

  await db.printJob.deleteMany({
    where: { id: { in: jobs.map((j) => j.id) } },
  });
  return jobs.length;
}
