"use client";

import { Button } from "@/components/atoms/Button";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-16">
      <div className="w-full max-w-md animate-fade-up rounded-xl border border-border bg-bg-panel/90 p-8 text-center shadow-[0_20px_60px_rgba(0,0,0,0.35)]">
        <p className="text-xs uppercase tracking-wide text-danger">Something went wrong</p>
        <h1 className="mt-2 font-[family-name:var(--font-display)] text-2xl tracking-tight">
          We hit an unexpected error
        </h1>
        <p className="mt-3 text-sm text-text-muted">
          {error.message || "Please try again. If this keeps happening, contact an admin."}
        </p>
        <div className="mt-6 flex justify-center gap-2">
          <Button type="button" onClick={reset}>
            Try again
          </Button>
          <Button type="button" variant="secondary" onClick={() => window.location.assign("/")}>
            Go home
          </Button>
        </div>
      </div>
    </div>
  );
}
