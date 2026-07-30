import { requireAdmin } from "@/lib/auth/guards";
import { getSession } from "@/lib/auth/session";
import { prisma } from "@/lib/db/prisma";
import { getPrinterStatusSnapshot } from "@/lib/services/printer-status";
import { AppShell } from "@/components/templates/AppShell";
import { PrinterStatusCard } from "@/components/organisms/PrinterStatusCard";
import { Badge } from "@/components/atoms/Badge";
import { UploadForm } from "@/components/molecules/UploadForm";
import Link from "next/link";

export default async function AdminDashboardPage() {
  const admin = await requireAdmin();
  const session = await getSession();
  const csrfToken = session.csrfToken ?? "";

  const [pending, printing, failed, users, printer] = await Promise.all([
    prisma.printJob.count({ where: { status: "pending" } }),
    prisma.printJob.count({ where: { status: { in: ["queued", "printing"] } } }),
    prisma.printJob.count({ where: { status: "failed" } }),
    prisma.user.count(),
    getPrinterStatusSnapshot(),
  ]);

  return (
    <AppShell
      username={admin.username}
      role={admin.role}
      csrfToken={csrfToken}
      title="Admin dashboard"
      subtitle="Overview of queue health, users, and admin print submission."
    >
      <div className="mb-6">
        <PrinterStatusCard printer={printer} />
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Pending approval" value={pending} href="/admin/jobs?status=pending" />
        <Stat label="In progress" value={printing} href="/admin/jobs" />
        <Stat label="Failed" value={failed} href="/admin/jobs?status=failed" />
        <Stat label="Users" value={users} href="/admin/users" />
      </div>

      <section className="rounded-lg border border-border bg-bg-panel/50 p-5">
        <h2 className="mb-1 text-lg font-medium">Admin print upload</h2>
        <p className="mb-4 text-sm text-text-muted">
          Submit as yourself. Automatic mode skips the approval queue.
        </p>
        <UploadForm csrfToken={csrfToken} />
      </section>
    </AppShell>
  );
}

function Stat({
  label,
  value,
  href,
}: {
  label: string;
  value: number;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-lg border border-border bg-bg-elevated/50 p-4 transition hover:border-accent/40"
    >
      <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-2 font-[family-name:var(--font-display)] text-3xl">{value}</p>
      <Badge tone="unknown">Open</Badge>
    </Link>
  );
}
