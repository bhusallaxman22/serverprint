"use client";

import { StatusBadge } from "@/components/molecules/StatusBadge";
import { SubmitButton } from "@/components/molecules/SubmitButton";
import { ActionForm } from "@/components/molecules/ActionForm";
import { cancelOwnJobAction, adminJobAction } from "@/app/actions";

export type JobRow = {
  jobUuid: string;
  status: string;
  originalFilename: string;
  pageCount: number;
  copies: number;
  submittedAt: string;
  failureReason: string | null;
  username?: string;
};

export function JobTable({
  jobs,
  csrfToken,
  admin = false,
}: {
  jobs: JobRow[];
  csrfToken: string;
  admin?: boolean;
}) {
  if (jobs.length === 0) {
    return (
      <p className="rounded-md border border-border/60 bg-bg-elevated/40 px-4 py-8 text-center text-sm text-text-muted">
        No jobs yet.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-bg-elevated text-xs uppercase tracking-wide text-text-muted">
          <tr>
            <th className="px-3 py-2.5 font-medium">File</th>
            {admin ? <th className="px-3 py-2.5 font-medium">User</th> : null}
            <th className="px-3 py-2.5 font-medium">Pages</th>
            <th className="px-3 py-2.5 font-medium">Status</th>
            <th className="px-3 py-2.5 font-medium">Submitted</th>
            <th className="px-3 py-2.5 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.jobUuid} className="border-t border-border/70">
              <td className="max-w-[220px] truncate px-3 py-2.5">{job.originalFilename}</td>
              {admin ? (
                <td className="px-3 py-2.5 text-text-muted">{job.username ?? "—"}</td>
              ) : null}
              <td className="px-3 py-2.5">
                {job.pageCount} × {job.copies}
              </td>
              <td className="px-3 py-2.5">
                <StatusBadge status={job.status} />
              </td>
              <td className="whitespace-nowrap px-3 py-2.5 text-text-muted">
                {new Date(job.submittedAt).toLocaleString()}
              </td>
              <td className="px-3 py-2.5">
                <div className="flex flex-wrap gap-1.5">
                  {!admin && !["completed", "cancelled", "rejected"].includes(job.status) ? (
                    <ActionForm action={cancelOwnJobAction} successMessage="Job cancelled.">
                      <input type="hidden" name="csrfToken" value={csrfToken} />
                      <input type="hidden" name="jobUuid" value={job.jobUuid} />
                      <SubmitButton variant="ghost" className="!px-2 !py-1 text-xs">
                        Cancel
                      </SubmitButton>
                    </ActionForm>
                  ) : null}
                  {admin && job.status === "pending" ? (
                    <>
                      <ActionForm action={adminJobAction} successMessage="Job approved.">
                        <input type="hidden" name="csrfToken" value={csrfToken} />
                        <input type="hidden" name="jobUuid" value={job.jobUuid} />
                        <input type="hidden" name="action" value="approve" />
                        <SubmitButton variant="primary" className="!px-2 !py-1 text-xs">
                          Approve
                        </SubmitButton>
                      </ActionForm>
                      <ActionForm
                        action={adminJobAction}
                        successMessage="Job rejected."
                        className="flex gap-1"
                      >
                        <input type="hidden" name="csrfToken" value={csrfToken} />
                        <input type="hidden" name="jobUuid" value={job.jobUuid} />
                        <input type="hidden" name="action" value="reject" />
                        <input
                          name="reason"
                          placeholder="Reason"
                          required
                          minLength={3}
                          className="w-28 rounded border border-border bg-bg px-2 py-1 text-xs"
                        />
                        <SubmitButton variant="danger" className="!px-2 !py-1 text-xs">
                          Reject
                        </SubmitButton>
                      </ActionForm>
                    </>
                  ) : null}
                  {admin && !["completed", "cancelled"].includes(job.status) ? (
                    <ActionForm action={adminJobAction} successMessage="Job cancelled.">
                      <input type="hidden" name="csrfToken" value={csrfToken} />
                      <input type="hidden" name="jobUuid" value={job.jobUuid} />
                      <input type="hidden" name="action" value="cancel" />
                      <SubmitButton variant="ghost" className="!px-2 !py-1 text-xs">
                        Cancel
                      </SubmitButton>
                    </ActionForm>
                  ) : null}
                  {admin && job.status === "failed" ? (
                    <ActionForm action={adminJobAction} successMessage="Job queued for retry.">
                      <input type="hidden" name="csrfToken" value={csrfToken} />
                      <input type="hidden" name="jobUuid" value={job.jobUuid} />
                      <input type="hidden" name="action" value="retry" />
                      <SubmitButton variant="secondary" className="!px-2 !py-1 text-xs">
                        Retry
                      </SubmitButton>
                    </ActionForm>
                  ) : null}
                </div>
                {job.failureReason ? (
                  <p className="mt-1 text-xs text-danger">{job.failureReason}</p>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
