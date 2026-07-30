import { type User, UserRole } from "@prisma/client";
import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth/session";
import { prisma } from "@/lib/db/prisma";
import { constantTimeEquals } from "@/lib/security";

export async function getCurrentUser(): Promise<User | null> {
  const session = await getSession();
  if (!session.isLoggedIn || !session.userId) return null;
  const user = await prisma.user.findUnique({ where: { id: session.userId } });
  if (!user || !user.isActive) return null;
  return user;
}

export async function requireUser(): Promise<User> {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  return user;
}

export async function requireAdmin(): Promise<User> {
  const user = await requireUser();
  if (user.role !== UserRole.admin) redirect("/dashboard");
  return user;
}

export async function requireCsrf(token: string | null | undefined): Promise<User> {
  const session = await getSession();
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (!session.csrfToken || !token || !constantTimeEquals(session.csrfToken, token)) {
    throw new Error("Invalid CSRF token.");
  }
  return user;
}

export function requirePrintApiKey(
  headerValue: string | null,
  expectedKey: string,
): boolean {
  if (!headerValue) return false;
  return constantTimeEquals(expectedKey, headerValue);
}
