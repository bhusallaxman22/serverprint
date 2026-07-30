"use server";

import path from "node:path";
import { mkdirSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { type User, UserRole } from "@prisma/client";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { config } from "@/lib/config";
import { getSession, newCsrfToken } from "@/lib/auth/session";
import { hashPassword, verifyPassword } from "@/lib/auth/password";
import { prisma } from "@/lib/db/prisma";
import { allowRateLimit } from "@/lib/services/rate-limit";
import { validateDocument, DocumentValidationError } from "@/lib/services/document";
import { QuotaExceededError, QuotaService } from "@/lib/services/quota";
import { CUPSService } from "@/lib/services/cups";
import {
  approveJob,
  cancelJob,
  createPendingJob,
  JobStateError,
  rejectJob,
  retryFailedJob,
} from "@/lib/services/jobs";
import { writeAuditLog } from "@/lib/services/audit";
import { writeFile } from "node:fs/promises";

function formString(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value : "";
}

async function requireSessionUser(): Promise<{ user: User; csrf: string }> {
  const session = await getSession();
  if (!session.isLoggedIn || !session.userId || !session.csrfToken) {
    redirect("/login");
  }
  const user = await prisma.user.findUnique({ where: { id: session.userId } });
  if (!user || !user.isActive) redirect("/login");
  return { user, csrf: session.csrfToken };
}

function assertCsrf(expected: string, provided: string) {
  if (!expected || expected !== provided) {
    throw new Error("Invalid CSRF token.");
  }
}

export async function loginAction(formData: FormData) {
  const username = formString(formData, "username").trim();
  const password = formString(formData, "password");
  const ip = "login";
  if (
    !allowRateLimit(`login:${ip}`, {
      limit: config.loginRateLimitPerMinute,
      windowSeconds: 60,
    })
  ) {
    throw new Error("Too many requests.");
  }

  const user = await prisma.user.findUnique({
    where: { usernameNormalized: username.toLowerCase() },
  });
  if (!user || !user.isActive || !(await verifyPassword(password, user.passwordHash))) {
    throw new Error("Invalid credentials.");
  }

  const session = await getSession();
  session.userId = user.id;
  session.isLoggedIn = true;
  session.csrfToken = newCsrfToken();
  await session.save();

  if (user.role === UserRole.admin) redirect("/admin/dashboard");
  redirect("/dashboard");
}

export async function logoutAction(formData: FormData) {
  const { csrf } = await requireSessionUser();
  assertCsrf(csrf, formString(formData, "csrfToken"));
  const session = await getSession();
  session.destroy();
  redirect("/login");
}

export async function uploadJobAction(formData: FormData) {
  const { user, csrf } = await requireSessionUser();
  assertCsrf(csrf, formString(formData, "csrfToken"));

  if (
    !allowRateLimit(`upload:${user.id}`, {
      limit: config.uploadRateLimitPerMinute,
      windowSeconds: 60,
    })
  ) {
    throw new Error("Too many requests.");
  }

  const copies = Math.min(100, Math.max(1, Number(formString(formData, "copies") || "1")));
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    throw new Error("File is required.");
  }
  if (file.size > config.maxUploadBytes) {
    throw new Error("File too large.");
  }

  const content = Buffer.from(await file.arrayBuffer());
  let metadata;
  try {
    metadata = await validateDocument(file.name || "document", file.type, content);
  } catch (err) {
    throw new Error(
      err instanceof DocumentValidationError ? err.message : "Invalid document.",
    );
  }

  mkdirSync(config.uploadsRoot, { recursive: true });
  const storedFilename = `${randomUUID()}${path.extname(file.name || "document").toLowerCase()}`;
  const storedPath = path.join(config.uploadsRoot, storedFilename);
  await writeFile(storedPath, content);

  try {
    await prisma.$transaction(async (tx) => {
      const pending = await createPendingJob(tx, {
        user,
        originalFilename: file.name || "document",
        storedFilename,
        metadata,
        copies,
        quotaService: new QuotaService(config.tz),
      });
      if (!user.requiresApproval) {
        await approveJob(tx, {
          actor: user,
          job: pending,
          cupsService: new CUPSService(config.cupsServer, config.printerName),
          filePath: storedPath,
        });
      }
    });
    revalidatePath("/dashboard");
    revalidatePath("/admin/jobs");
    revalidatePath("/admin/dashboard");
    return;
  } catch (err) {
    try {
      const { unlink } = await import("node:fs/promises");
      await unlink(storedPath);
    } catch {
      /* ignore */
    }
    if (err instanceof QuotaExceededError) throw new Error(err.message);
    throw err;
  }
}

export async function createUserAction(formData: FormData) {
  const { user: admin, csrf } = await requireSessionUser();
  assertCsrf(csrf, formString(formData, "csrfToken"));
  if (admin.role !== UserRole.admin) throw new Error("Admin permission required.");

  const username = formString(formData, "username").trim();
  const password = formString(formData, "password");
  const role = formString(formData, "role") === "admin" ? UserRole.admin : UserRole.user;
  const dailyPageQuota = Number(formString(formData, "dailyPageQuota") || "250");
  const weeklyPageQuota = Number(formString(formData, "weeklyPageQuota") || "1000");
  const requiresApproval = formString(formData, "requiresApproval") === "on";
  const printMode = formString(formData, "printMode") === "color" ? "color" : "bw";
  const mustChangePassword = formString(formData, "mustChangePassword") === "on";
  const isActive = formString(formData, "isActive") !== "off";

  if (!/^[A-Za-z0-9._-]{3,64}$/.test(username)) {
    throw new Error("Username must be 3–64 characters and use only letters, numbers, . _ -");
  }
  if (password.length < 8) throw new Error("Password must be at least 8 characters.");

  const existing = await prisma.user.findUnique({
    where: { usernameNormalized: username.toLowerCase() },
  });
  if (existing) throw new Error("Username already exists.");

  const created = await prisma.user.create({
    data: {
      username,
      usernameNormalized: username.toLowerCase(),
      passwordHash: await hashPassword(password),
      role,
      isActive,
      mustChangePassword,
      dailyPageQuota,
      weeklyPageQuota,
      requiresApproval,
      printMode,
    },
  });

  await writeAuditLog(prisma, {
    action: "user_created",
    targetType: "user",
    targetId: String(created.id),
    actorUserId: admin.id,
    details: {
      username: created.username,
      role: created.role,
      requiresApproval: created.requiresApproval,
    },
  });

  revalidatePath("/admin/users");
  return;
}

export async function updateUserAction(formData: FormData) {
  const { user: admin, csrf } = await requireSessionUser();
  assertCsrf(csrf, formString(formData, "csrfToken"));
  if (admin.role !== UserRole.admin) throw new Error("Admin permission required.");

  const userId = Number(formString(formData, "userId"));
  const user = await prisma.user.findUnique({ where: { id: userId } });
  if (!user) throw new Error("User not found.");

  const role = formString(formData, "role") === "admin" ? UserRole.admin : UserRole.user;
  const isActive = formString(formData, "isActive") === "on";
  const requiresApproval = formString(formData, "requiresApproval") === "on";
  const printMode = formString(formData, "printMode") === "color" ? "color" : "bw";
  const dailyPageQuota = Number(formString(formData, "dailyPageQuota") || user.dailyPageQuota);
  const weeklyPageQuota = Number(formString(formData, "weeklyPageQuota") || user.weeklyPageQuota);
  const resetPassword = formString(formData, "resetPassword") === "on";
  const tempPassword = formString(formData, "tempPassword");

  if (user.role === UserRole.admin && (role !== UserRole.admin || !isActive)) {
    const activeAdmins = await prisma.user.count({
      where: { role: UserRole.admin, isActive: true },
    });
    if (activeAdmins <= 1) {
      throw new Error("Cannot disable or demote the last active admin.");
    }
  }

  const data: Record<string, unknown> = {
    role,
    isActive,
    requiresApproval,
    printMode,
    dailyPageQuota,
    weeklyPageQuota,
  };

  if (resetPassword) {
    if (tempPassword.length < 8) throw new Error("Temp password must be at least 8 characters.");
    data.passwordHash = await hashPassword(tempPassword);
    data.mustChangePassword = true;
  }

  await prisma.user.update({ where: { id: user.id }, data });
  await writeAuditLog(prisma, {
    action: "user_updated",
    targetType: "user",
    targetId: String(user.id),
    actorUserId: admin.id,
    details: { role, isActive, requiresApproval, printMode, resetPassword },
  });

  revalidatePath("/admin/users");
  return;
}

export async function adminJobAction(formData: FormData) {
  const { user: admin, csrf } = await requireSessionUser();
  assertCsrf(csrf, formString(formData, "csrfToken"));
  if (admin.role !== UserRole.admin) throw new Error("Admin permission required.");

  const jobUuid = formString(formData, "jobUuid");
  const action = formString(formData, "action");
  const reason = formString(formData, "reason") || "Rejected by admin";

  const job = await prisma.printJob.findUnique({
    where: { jobUuid },
    include: { user: true },
  });
  if (!job) throw new Error("Job not found.");

  const cups = new CUPSService(config.cupsServer, config.printerName);
  const filePath = path.join(config.uploadsRoot, job.storedFilename);

  try {
    if (action === "approve") {
      await approveJob(prisma, { actor: admin, job, cupsService: cups, filePath });
    } else if (action === "reject") {
      await rejectJob(prisma, { actor: admin, job, reason });
    } else if (action === "cancel") {
      await cancelJob(prisma, { actor: admin, job, cupsService: cups });
    } else if (action === "retry") {
      const { access } = await import("node:fs/promises");
      let fileExists = true;
      try {
        await access(filePath);
      } catch {
        fileExists = false;
      }
      await retryFailedJob(prisma, {
        actor: admin,
        job,
        fileExists,
        quotaService: new QuotaService(config.tz),
        allowRetry: config.allowFailedJobRetry,
        maxRetries: config.maxJobRetries,
      });
    } else {
      throw new Error("Unknown action.");
    }
  } catch (err) {
    if (err instanceof JobStateError) throw new Error(err.message);
    throw err;
  }

  revalidatePath("/admin/jobs");
  revalidatePath("/admin/dashboard");
  revalidatePath("/dashboard");
  return;
}

export async function cancelOwnJobAction(formData: FormData) {
  const { user, csrf } = await requireSessionUser();
  assertCsrf(csrf, formString(formData, "csrfToken"));
  const jobUuid = formString(formData, "jobUuid");
  const job = await prisma.printJob.findFirst({
    where: { jobUuid, userId: user.id },
  });
  if (!job) throw new Error("Job not found.");
  try {
    await cancelJob(prisma, {
      actor: user,
      job,
      cupsService: new CUPSService(config.cupsServer, config.printerName),
    });
  } catch (err) {
    if (err instanceof JobStateError) throw new Error(err.message);
    throw err;
  }
  revalidatePath("/dashboard");
  return;
}

export async function updatePrintModeAction(formData: FormData) {
  const { user, csrf } = await requireSessionUser();
  assertCsrf(csrf, formString(formData, "csrfToken"));
  const printMode = formString(formData, "printMode") === "color" ? "color" : "bw";
  await prisma.user.update({ where: { id: user.id }, data: { printMode } });
  revalidatePath("/dashboard");
  return;
}
