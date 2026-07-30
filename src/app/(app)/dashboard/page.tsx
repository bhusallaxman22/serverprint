import { requireUser } from "@/lib/auth/guards";
import { getSession } from "@/lib/auth/session";
import { prisma } from "@/lib/db/prisma";
import { config } from "@/lib/config";
import { QuotaService } from "@/lib/services/quota";
import { getPrinterStatusSnapshot } from "@/lib/services/printer-status";
import { AppShell } from "@/components/templates/AppShell";
import { UploadForm } from "@/components/molecules/UploadForm";
import { JobTable } from "@/components/molecules/JobTable";
import { PrinterStatusCard } from "@/components/organisms/PrinterStatusCard";
import { Select } from "@/components/atoms/Select";
import { SubmitButton } from "@/components/molecules/SubmitButton";
import { updatePrintModeAction } from "@/app/actions";

export default async function UserDashboardPage() {
  const user = await requireUser();
  const session = await getSession();
  const csrfToken = session.csrfToken ?? "";

  const [jobs, usage, printer] = await Promise.all([
    prisma.printJob.findMany({
      where: { userId: user.id },
      orderBy: { submittedAt: "desc" },
      take: 25,
    }),
    new QuotaService(config.tz).getUsageForUser(prisma, user),
    getPrinterStatusSnapshot(),
  ]);

  return (
    <AppShell
      username={user.username}
      role={user.role}
      csrfToken={csrfToken}
      title="Print dashboard"
      subtitle={`Welcome, ${user.username}. Upload a document to print.`}
    >
      <div className="mb-6">
        <PrinterStatusCard printer={printer} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-border bg-bg-panel/50 p-5">
          <h2 className="mb-1 text-lg font-medium">Submit print</h2>
          <p className="mb-4 text-sm text-text-muted">
            Mode: {user.requiresApproval ? "manual approval" : "automatic"} ·{" "}
            {user.printMode.toUpperCase()}
          </p>
          <UploadForm csrfToken={csrfToken} />
          <form action={updatePrintModeAction} className="mt-4 flex items-end gap-2">
            <input type="hidden" name="csrfToken" value={csrfToken} />
            <Select
              label="Print mode"
              name="printMode"
              defaultValue={user.printMode}
              options={[
                { value: "bw", label: "Black & white" },
                { value: "color", label: "Color" },
              ]}
            />
            <SubmitButton variant="secondary">Save</SubmitButton>
          </form>
        </section>

        <section className="rounded-lg border border-border bg-bg-panel/50 p-5">
          <h2 className="mb-4 text-lg font-medium">Quotas</h2>
          <div className="space-y-4">
            <QuotaBar
              label="Daily"
              used={usage.dailyUsed}
              limit={user.dailyPageQuota}
            />
            <QuotaBar
              label="Weekly"
              used={usage.weeklyUsed}
              limit={user.weeklyPageQuota}
            />
          </div>
          <p className="mt-4 text-xs text-text-muted">
            Rejected, failed, and cancelled jobs release quota automatically.
          </p>
        </section>
      </div>

      <section className="mt-6">
        <h2 className="mb-3 text-lg font-medium">Recent jobs</h2>
        <JobTable
          csrfToken={csrfToken}
          jobs={jobs.map((j) => ({
            jobUuid: j.jobUuid,
            status: j.status,
            originalFilename: j.originalFilename,
            pageCount: j.pageCount,
            copies: j.copies,
            submittedAt: j.submittedAt.toISOString(),
            failureReason: j.failureReason,
          }))}
        />
      </section>
    </AppShell>
  );
}

function QuotaBar({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number;
}) {
  const pct = Math.min(100, Math.round((used / Math.max(limit, 1)) * 100));
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-text-muted">
          {used} / {limit} pages
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-bg">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
