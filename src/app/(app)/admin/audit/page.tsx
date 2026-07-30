import { requireAdmin } from "@/lib/auth/guards";
import { getSession } from "@/lib/auth/session";
import { prisma } from "@/lib/db/prisma";
import { AppShell } from "@/components/templates/AppShell";

export default async function AuditLogPage() {
  const admin = await requireAdmin();
  const session = await getSession();
  const csrfToken = session.csrfToken ?? "";

  const logs = await prisma.auditLog.findMany({
    include: { actor: true },
    orderBy: { createdAt: "desc" },
    take: 200,
  });

  return (
    <AppShell
      username={admin.username}
      role={admin.role}
      csrfToken={csrfToken}
      title="Audit log"
      subtitle="Security-relevant actions across users and print jobs."
    >
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-bg-elevated text-xs uppercase tracking-wide text-text-muted">
            <tr>
              <th className="px-3 py-2.5 font-medium">When</th>
              <th className="px-3 py-2.5 font-medium">Actor</th>
              <th className="px-3 py-2.5 font-medium">Action</th>
              <th className="px-3 py-2.5 font-medium">Target</th>
              <th className="px-3 py-2.5 font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-t border-border/70 align-top">
                <td className="whitespace-nowrap px-3 py-2.5 text-text-muted">
                  {log.createdAt.toLocaleString()}
                </td>
                <td className="px-3 py-2.5">{log.actor?.username ?? "system"}</td>
                <td className="px-3 py-2.5 font-medium">{log.action}</td>
                <td className="px-3 py-2.5 text-text-muted">
                  {log.targetType}
                  {log.targetId ? `:${log.targetId}` : ""}
                </td>
                <td className="max-w-md px-3 py-2.5 font-mono text-xs text-text-muted">
                  {log.details}
                </td>
              </tr>
            ))}
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-8 text-center text-text-muted">
                  No audit events yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
