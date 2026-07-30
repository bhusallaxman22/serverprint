import { Sidebar } from "@/components/organisms/Sidebar";

export function AppShell({
  children,
  username,
  role,
  csrfToken,
  title,
  subtitle,
}: {
  children: React.ReactNode;
  username: string;
  role: string;
  csrfToken: string;
  title: string;
  subtitle?: string;
}) {
  const items =
    role === "admin"
      ? [
          { href: "/admin/dashboard", label: "Dashboard" },
          { href: "/admin/jobs", label: "Print jobs" },
          { href: "/admin/users", label: "Users" },
          { href: "/admin/audit", label: "Audit log" },
          { href: "/dashboard", label: "My print" },
        ]
      : [{ href: "/dashboard", label: "Dashboard" }];

  return (
    <div className="flex min-h-screen">
      <Sidebar items={items} username={username} role={role} csrfToken={csrfToken} />
      <main className="flex-1 px-4 pb-10 pt-14 md:px-8 md:pt-8">
        <header className="mb-6 animate-fade-up">
          <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-tight text-text">
            {title}
          </h1>
          {subtitle ? <p className="mt-1 text-sm text-text-muted">{subtitle}</p> : null}
        </header>
        <div className="animate-fade-up [animation-delay:80ms]">{children}</div>
      </main>
    </div>
  );
}
