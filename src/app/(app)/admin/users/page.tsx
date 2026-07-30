import { requireAdmin } from "@/lib/auth/guards";
import { getSession } from "@/lib/auth/session";
import { prisma } from "@/lib/db/prisma";
import { AppShell } from "@/components/templates/AppShell";
import { Input } from "@/components/atoms/Input";
import { Select } from "@/components/atoms/Select";
import { SubmitButton } from "@/components/molecules/SubmitButton";
import { ActionForm } from "@/components/molecules/ActionForm";
import { Badge } from "@/components/atoms/Badge";
import { createUserAction, updateUserAction } from "@/app/actions";

export default async function AdminUsersPage() {
  const admin = await requireAdmin();
  const session = await getSession();
  const csrfToken = session.csrfToken ?? "";
  const users = await prisma.user.findMany({ orderBy: { createdAt: "asc" } });

  return (
    <AppShell
      username={admin.username}
      role={admin.role}
      csrfToken={csrfToken}
      title="Users"
      subtitle="Create accounts, set quotas, print mode, and approval policy."
    >
      <section className="mb-8 rounded-lg border border-border bg-bg-panel/50 p-5">
        <h2 className="mb-4 text-lg font-medium">Create user</h2>
        <ActionForm
          action={createUserAction}
          successMessage="User created."
          resetOnSuccess
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
        >
          <input type="hidden" name="csrfToken" value={csrfToken} />
          <Input label="Username" name="username" required minLength={3} maxLength={64} />
          <Input label="Password" name="password" type="password" required minLength={8} />
          <Select
            label="Role"
            name="role"
            options={[
              { value: "user", label: "User" },
              { value: "admin", label: "Admin" },
            ]}
          />
          <Input
            label="Daily page quota"
            name="dailyPageQuota"
            type="number"
            defaultValue={250}
            min={1}
          />
          <Input
            label="Weekly page quota"
            name="weeklyPageQuota"
            type="number"
            defaultValue={1000}
            min={1}
          />
          <Select
            label="Print mode"
            name="printMode"
            options={[
              { value: "bw", label: "Black & white" },
              { value: "color", label: "Color" },
            ]}
          />
          <label className="flex items-center gap-2 text-sm text-text-muted">
            <input type="checkbox" name="requiresApproval" defaultChecked className="accent-accent" />
            Requires manual approval
          </label>
          <label className="flex items-center gap-2 text-sm text-text-muted">
            <input type="checkbox" name="mustChangePassword" className="accent-accent" />
            Must change password
          </label>
          <div className="sm:col-span-2 lg:col-span-3">
            <SubmitButton>Create user</SubmitButton>
          </div>
        </ActionForm>
      </section>

      <div className="space-y-4">
        {users.map((user) => (
          <ActionForm
            key={user.id}
            action={updateUserAction}
            successMessage={`Updated ${user.username}.`}
            className="rounded-lg border border-border bg-bg-elevated/40 p-4"
          >
            <input type="hidden" name="csrfToken" value={csrfToken} />
            <input type="hidden" name="userId" value={user.id} />
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <p className="font-medium">{user.username}</p>
              <Badge tone={user.role}>{user.role}</Badge>
              <Badge tone={user.isActive ? "online" : "offline"}>
                {user.isActive ? "active" : "disabled"}
              </Badge>
              <Badge tone={user.requiresApproval ? "pending" : "completed"}>
                {user.requiresApproval ? "manual" : "automatic"}
              </Badge>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Select
                label="Role"
                name="role"
                defaultValue={user.role}
                options={[
                  { value: "user", label: "User" },
                  { value: "admin", label: "Admin" },
                ]}
              />
              <Select
                label="Print mode"
                name="printMode"
                defaultValue={user.printMode}
                options={[
                  { value: "bw", label: "Black & white" },
                  { value: "color", label: "Color" },
                ]}
              />
              <Input
                label="Daily quota"
                name="dailyPageQuota"
                type="number"
                defaultValue={user.dailyPageQuota}
                min={1}
              />
              <Input
                label="Weekly quota"
                name="weeklyPageQuota"
                type="number"
                defaultValue={user.weeklyPageQuota}
                min={1}
              />
              <label className="flex items-center gap-2 text-sm text-text-muted">
                <input
                  type="checkbox"
                  name="isActive"
                  defaultChecked={user.isActive}
                  className="accent-accent"
                />
                Active
              </label>
              <label className="flex items-center gap-2 text-sm text-text-muted">
                <input
                  type="checkbox"
                  name="requiresApproval"
                  defaultChecked={user.requiresApproval}
                  className="accent-accent"
                />
                Requires approval
              </label>
              <label className="flex items-center gap-2 text-sm text-text-muted">
                <input type="checkbox" name="resetPassword" className="accent-accent" />
                Reset password
              </label>
              <Input label="Temp password" name="tempPassword" type="password" minLength={8} />
            </div>
            <div className="mt-3">
              <SubmitButton variant="secondary">Save changes</SubmitButton>
            </div>
          </ActionForm>
        ))}
      </div>
    </AppShell>
  );
}
