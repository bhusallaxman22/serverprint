import { requireAdmin } from "@/lib/auth/guards";
import { getSession } from "@/lib/auth/session";
import { prisma } from "@/lib/db/prisma";
import { AppShell } from "@/components/templates/AppShell";
import { JobTable } from "@/components/molecules/JobTable";
import type { PrintJobStatus } from "@prisma/client";
import Link from "next/link";

const FILTERS = [
  "all",
  "pending",
  "queued",
  "printing",
  "completed",
  "failed",
  "rejected",
  "cancelled",
] as const;

type SearchParams = Promise<{ status?: string }>;

export default async function AdminJobsPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const admin = await requireAdmin();
  const session = await getSession();
  const csrfToken = session.csrfToken ?? "";
  const params = await searchParams;
  const status = FILTERS.includes(params.status as (typeof FILTERS)[number])
    ? params.status
    : "all";

  const jobs = await prisma.printJob.findMany({
    where: status === "all" ? undefined : { status: status as PrintJobStatus },
    include: { user: true },
    orderBy: { submittedAt: "desc" },
    take: 100,
  });

  return (
    <AppShell
      username={admin.username}
      role={admin.role}
      csrfToken={csrfToken}
      title="Print jobs"
      subtitle="Approve, reject, cancel, or retry jobs across the fleet."
    >
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <Link
            key={f}
            href={f === "all" ? "/admin/jobs" : `/admin/jobs?status=${f}`}
            className={`rounded-md px-3 py-1.5 text-xs uppercase tracking-wide ${
              status === f
                ? "bg-accent/15 text-accent"
                : "bg-bg-elevated text-text-muted hover:text-text"
            }`}
          >
            {f}
          </Link>
        ))}
      </div>
      <JobTable
        admin
        csrfToken={csrfToken}
        jobs={jobs.map((j) => ({
          jobUuid: j.jobUuid,
          status: j.status,
          originalFilename: j.originalFilename,
          pageCount: j.pageCount,
          copies: j.copies,
          submittedAt: j.submittedAt.toISOString(),
          failureReason: j.failureReason,
          username: j.user.username,
        }))}
      />
    </AppShell>
  );
}
