"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/atoms/Logo";
import { logoutAction } from "@/app/actions";
import { ActionForm } from "@/components/molecules/ActionForm";
import { SubmitButton } from "@/components/molecules/SubmitButton";

type NavItem = { href: string; label: string };

export function Sidebar({
  items,
  username,
  role,
  csrfToken,
}: {
  items: NavItem[];
  username: string;
  role: string;
  csrfToken: string;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem("printdrop.sidebar.collapsed");
    if (stored === "1") setCollapsed(true);
  }, []);

  useEffect(() => {
    window.localStorage.setItem("printdrop.sidebar.collapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const nav = (
    <nav className="flex flex-1 flex-col gap-1 px-2 py-3">
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-md px-3 py-2 text-sm transition ${
              active
                ? "bg-accent/15 text-accent"
                : "text-text-muted hover:bg-white/5 hover:text-text"
            } ${collapsed ? "text-center" : ""}`}
            title={item.label}
          >
            {collapsed ? item.label.slice(0, 1) : item.label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <>
      <button
        type="button"
        className="fixed left-3 top-3 z-40 rounded-md border border-border bg-bg-panel px-2.5 py-1.5 text-xs text-text md:hidden"
        onClick={() => setMobileOpen((v) => !v)}
        aria-label="Toggle navigation"
      >
        Menu
      </button>

      {mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-border bg-sidebar transition-all duration-300 md:static ${
          collapsed ? "md:w-[72px]" : "md:w-60"
        } ${mobileOpen ? "w-64 translate-x-0" : "w-64 -translate-x-full md:translate-x-0"}`}
      >
        <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-4">
          <Logo compact={collapsed} />
          <button
            type="button"
            className="hidden rounded-md px-2 py-1 text-xs text-text-muted hover:bg-white/5 hover:text-text md:inline-flex"
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>
        {nav}
        <div className="border-t border-border p-3">
          {!collapsed ? (
            <p className="mb-2 truncate text-xs text-text-muted">
              {username} · {role}
            </p>
          ) : null}
          <ActionForm action={logoutAction} successMessage="Signed out.">
            <input type="hidden" name="csrfToken" value={csrfToken} />
            <SubmitButton variant="ghost" className="w-full !justify-start">
              {collapsed ? "⎋" : "Sign out"}
            </SubmitButton>
          </ActionForm>
        </div>
      </aside>
    </>
  );
}
