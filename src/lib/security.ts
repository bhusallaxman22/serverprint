import { timingSafeEqual } from "node:crypto";

export function constantTimeEquals(left: string, right: string): boolean {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

export function serializeUser(user: {
  id: number;
  username: string;
  role: string;
  isActive: boolean;
  mustChangePassword: boolean;
  requiresApproval: boolean;
  printMode: string;
  dailyPageQuota: number;
  weeklyPageQuota: number;
}) {
  return {
    id: user.id,
    username: user.username,
    role: user.role,
    isActive: user.isActive,
    mustChangePassword: user.mustChangePassword,
    requiresApproval: user.requiresApproval,
    printMode: user.printMode,
    dailyPageQuota: user.dailyPageQuota,
    weeklyPageQuota: user.weeklyPageQuota,
  };
}

export function serializeJob(job: {
  jobUuid: string;
  status: string;
  originalFilename: string;
  mimeType: string;
  pageCount: number;
  copies: number;
  submittedAt: Date;
  failureReason: string | null;
  userId?: number;
  retryCount?: number;
}) {
  return {
    jobUuid: job.jobUuid,
    status: job.status,
    originalFilename: job.originalFilename,
    mimeType: job.mimeType,
    pageCount: job.pageCount,
    copies: job.copies,
    submittedAt: job.submittedAt.toISOString(),
    failureReason: job.failureReason,
    userId: job.userId,
    retryCount: job.retryCount,
  };
}
