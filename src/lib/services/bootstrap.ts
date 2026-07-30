import { UserRole } from "@prisma/client";
import { config } from "@/lib/config";
import { hashPassword } from "@/lib/auth/password";
import { prisma } from "@/lib/db/prisma";

const DEFAULT_ADMIN_PASSWORD = "admin123456";

export async function bootstrapAdmin(): Promise<void> {
  const adminCount = await prisma.user.count({ where: { role: UserRole.admin } });
  if (adminCount > 0) return;

  if (config.adminPassword === DEFAULT_ADMIN_PASSWORD) {
    console.warn("Bootstrap admin password matches default value. Rotate immediately.");
  }

  await prisma.user.create({
    data: {
      username: config.adminUsername,
      usernameNormalized: config.adminUsername.toLowerCase(),
      passwordHash: await hashPassword(config.adminPassword),
      role: UserRole.admin,
      isActive: true,
      mustChangePassword: config.forcePasswordChangeDefault,
      requiresApproval: false,
    },
  });
}
