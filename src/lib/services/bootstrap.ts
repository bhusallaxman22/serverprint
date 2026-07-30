import { Prisma, UserRole } from "@prisma/client";
import { config } from "@/lib/config";
import { hashPassword } from "@/lib/auth/password";
import { prisma } from "@/lib/db/prisma";

const DEFAULT_ADMIN_PASSWORD = "admin123456";

function isUniqueConstraintError(error: unknown): boolean {
  return error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002";
}

/**
 * Ensure a bootstrap admin exists. Idempotent: safe under concurrent
 * instrumentation/worker startup. Never updates an existing user's password.
 */
export async function bootstrapAdmin(): Promise<void> {
  const usernameNormalized = config.adminUsername.toLowerCase();

  const existing = await prisma.user.findFirst({
    where: {
      OR: [{ role: UserRole.admin }, { usernameNormalized }],
    },
    select: { id: true },
  });
  if (existing) return;

  if (config.adminPassword === DEFAULT_ADMIN_PASSWORD) {
    console.warn("Bootstrap admin password matches default value. Rotate immediately.");
  }

  try {
    await prisma.user.create({
      data: {
        username: config.adminUsername,
        usernameNormalized,
        passwordHash: await hashPassword(config.adminPassword),
        role: UserRole.admin,
        isActive: true,
        mustChangePassword: config.forcePasswordChangeDefault,
        requiresApproval: false,
      },
    });
  } catch (error) {
    // Concurrent bootstrap (web + worker, or double instrumentation) lost the race.
    if (isUniqueConstraintError(error)) return;
    throw error;
  }
}
