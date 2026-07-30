import type { Prisma, PrismaClient } from "@prisma/client";

type DbClient = PrismaClient | Prisma.TransactionClient;

export async function writeAuditLog(
  db: DbClient,
  params: {
    action: string;
    targetType: string;
    targetId?: string | null;
    actorUserId?: number | null;
    details?: Record<string, unknown>;
  },
) {
  return db.auditLog.create({
    data: {
      action: params.action,
      targetType: params.targetType,
      targetId: params.targetId ?? null,
      actorUserId: params.actorUserId ?? null,
      details: JSON.stringify(params.details ?? {}),
    },
  });
}
