import {
  type PrintJob,
  PrintJobStatus,
  type Prisma,
  type PrismaClient,
  type User,
} from "@prisma/client";
import type { PathLike } from "node:fs";
import { writeAuditLog } from "@/lib/services/audit";
import { CUPSService, CUPSServiceError } from "@/lib/services/cups";
import type { DocumentMetadata } from "@/lib/services/document";
import { QuotaService } from "@/lib/services/quota";

type DbClient = PrismaClient | Prisma.TransactionClient;

export class JobStateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "JobStateError";
  }
}

export async function createPendingJob(
  db: DbClient,
  params: {
    user: User;
    originalFilename: string;
    storedFilename: string;
    metadata: DocumentMetadata;
    copies: number;
    quotaService: QuotaService;
  },
): Promise<PrintJob> {
  const timestamp = new Date();
  await params.quotaService.ensureQuotaForNewJob(
    db,
    params.user,
    params.metadata.pageCount * params.copies,
    timestamp,
  );

  const job = await db.printJob.create({
    data: {
      userId: params.user.id,
      originalFilename: params.originalFilename,
      storedFilename: params.storedFilename,
      mimeType: params.metadata.mimeType,
      extension: params.metadata.extension,
      pageCount: params.metadata.pageCount,
      copies: params.copies,
      status: PrintJobStatus.pending,
      submittedAt: timestamp,
    },
  });

  await writeAuditLog(db, {
    action: "job_submitted",
    targetType: "print_job",
    targetId: job.jobUuid,
    actorUserId: params.user.id,
  });

  return job;
}

export async function approveJob(
  db: DbClient,
  params: {
    actor: User;
    job: PrintJob;
    cupsService: CUPSService;
    filePath: PathLike;
  },
): Promise<PrintJob> {
  if (params.job.status !== PrintJobStatus.pending) {
    throw new JobStateError("Only pending jobs can be approved.");
  }

  const now = new Date();
  let cupsId: string;
  try {
    cupsId = await params.cupsService.submitJob(
      params.filePath,
      params.job.originalFilename,
      params.job.copies,
    );
  } catch (err) {
    if (!(err instanceof CUPSServiceError)) throw err;
    const failed = await db.printJob.update({
      where: { id: params.job.id },
      data: {
        status: PrintJobStatus.failed,
        failureReason: "Failed to queue print job.",
        approvedAt: now,
        approvedByUserId: params.actor.id,
      },
    });
    await writeAuditLog(db, {
      action: "job_failed_to_queue",
      targetType: "print_job",
      targetId: failed.jobUuid,
      actorUserId: params.actor.id,
    });
    return failed;
  }

  const queued = await db.printJob.update({
    where: { id: params.job.id },
    data: {
      status: PrintJobStatus.queued,
      cupsJobId: cupsId,
      approvedAt: now,
      approvedByUserId: params.actor.id,
      failureReason: null,
    },
  });

  await writeAuditLog(db, {
    action: "job_approved",
    targetType: "print_job",
    targetId: queued.jobUuid,
    actorUserId: params.actor.id,
  });

  return queued;
}

export async function rejectJob(
  db: DbClient,
  params: { actor: User; job: PrintJob; reason: string },
): Promise<PrintJob> {
  if (params.job.status !== PrintJobStatus.pending) {
    throw new JobStateError("Only pending jobs can be rejected.");
  }
  const rejected = await db.printJob.update({
    where: { id: params.job.id },
    data: {
      status: PrintJobStatus.rejected,
      rejectedAt: new Date(),
      rejectedByUserId: params.actor.id,
      failureReason: params.reason,
    },
  });
  await writeAuditLog(db, {
    action: "job_rejected",
    targetType: "print_job",
    targetId: rejected.jobUuid,
    actorUserId: params.actor.id,
    details: { reason: params.reason },
  });
  return rejected;
}

export async function cancelJob(
  db: DbClient,
  params: { actor: User; job: PrintJob; cupsService?: CUPSService },
): Promise<PrintJob> {
  if (
    params.job.status === PrintJobStatus.completed ||
    params.job.status === PrintJobStatus.cancelled
  ) {
    throw new JobStateError("Job cannot be cancelled.");
  }

  if (
    params.cupsService &&
    params.job.cupsJobId &&
    (params.job.status === PrintJobStatus.queued ||
      params.job.status === PrintJobStatus.printing)
  ) {
    try {
      await params.cupsService.cancelCupsJob(params.job.cupsJobId);
    } catch {
      // Best-effort cancel against CUPS; still mark cancelled locally.
    }
  }

  const cancelled = await db.printJob.update({
    where: { id: params.job.id },
    data: { status: PrintJobStatus.cancelled },
  });
  await writeAuditLog(db, {
    action: "job_cancelled",
    targetType: "print_job",
    targetId: cancelled.jobUuid,
    actorUserId: params.actor.id,
  });
  return cancelled;
}

export async function syncQueuedJobsFromCups(
  db: DbClient,
  cupsService: CUPSService,
  asOf: Date = new Date(),
): Promise<number> {
  const activeStates = await cupsService.fetchJobStates();
  if (activeStates === null) return 0;

  const activeIds = new Set(activeStates.map((s) => s.cupsJobId));
  const jobs = await db.printJob.findMany({
    where: { status: { in: [PrintJobStatus.queued, PrintJobStatus.printing] } },
  });

  let updated = 0;
  for (const job of jobs) {
    if (!job.cupsJobId) continue;
    if (activeIds.has(job.cupsJobId)) {
      if (job.status !== PrintJobStatus.printing) {
        await db.printJob.update({
          where: { id: job.id },
          data: { status: PrintJobStatus.printing, updatedAt: asOf },
        });
        updated += 1;
      }
      continue;
    }
    await db.printJob.update({
      where: { id: job.id },
      data: { status: PrintJobStatus.completed, updatedAt: asOf },
    });
    updated += 1;
  }
  return updated;
}

export async function retryFailedJob(
  db: DbClient,
  params: {
    actor: User;
    job: PrintJob & { user: User };
    fileExists: boolean;
    quotaService: QuotaService;
    allowRetry: boolean;
    maxRetries: number;
  },
): Promise<PrintJob> {
  if (!params.allowRetry) throw new JobStateError("Retry policy is disabled.");
  if (params.job.status !== PrintJobStatus.failed) {
    throw new JobStateError("Only failed jobs can be retried.");
  }
  if (params.job.retryCount >= params.maxRetries) {
    throw new JobStateError("Maximum retries reached for this job.");
  }
  if (!params.fileExists) {
    throw new JobStateError("Original document is unavailable for retry.");
  }

  await params.quotaService.ensureQuotaForNewJob(
    db,
    params.job.user,
    params.job.pageCount * params.job.copies,
    new Date(),
  );

  const previousStatus = params.job.status;
  const retried = await db.printJob.update({
    where: { id: params.job.id },
    data: {
      status: PrintJobStatus.pending,
      failureReason: null,
      cupsJobId: null,
      approvedAt: null,
      approvedByUserId: null,
      rejectedAt: null,
      rejectedByUserId: null,
      retryCount: { increment: 1 },
      retriedAt: new Date(),
      retriedByUserId: params.actor.id,
    },
  });

  await writeAuditLog(db, {
    action: "job_retried",
    targetType: "print_job",
    targetId: retried.jobUuid,
    actorUserId: params.actor.id,
    details: {
      from_status: previousStatus,
      to_status: retried.status,
      retry_count: retried.retryCount,
    },
  });

  return retried;
}
