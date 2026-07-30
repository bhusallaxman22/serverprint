export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden>
          <path
            d="M7 8V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v3M7 16v3a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-3"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <rect x="4" y="8" width="16" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
          <circle cx="17" cy="12" r="1" fill="currentColor" />
        </svg>
      </div>
      {!compact ? (
        <div>
          <p className="font-[family-name:var(--font-display)] text-lg leading-none tracking-tight text-text">
            PrintDrop
          </p>
          <p className="mt-0.5 text-[11px] text-text-muted">CUPS print intake</p>
        </div>
      ) : null}
    </div>
  );
}
