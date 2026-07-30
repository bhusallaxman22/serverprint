import { Logo } from "@/components/atoms/Logo";
import { Input } from "@/components/atoms/Input";
import { SubmitButton } from "@/components/molecules/SubmitButton";
import { loginAction } from "@/app/actions";

export function LoginTemplate() {
  return (
    <div className="relative flex min-h-screen items-center justify-center px-4">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(900px_500px_at_15%_10%,rgba(61,214,198,0.12),transparent_55%),radial-gradient(700px_400px_at_90%_0%,rgba(80,120,200,0.1),transparent_50%),linear-gradient(180deg,#0c1117_0%,#101820_100%)]"
      />
      <div className="relative w-full max-w-md animate-fade-up rounded-xl border border-border bg-bg-panel/90 p-8 shadow-[0_20px_60px_rgba(0,0,0,0.35)] backdrop-blur">
        <div className="mb-8">
          <Logo />
        </div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
          Sign in
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Session cookies only — no API keys in the browser.
        </p>
        <form action={loginAction} className="mt-6 space-y-4">
          <Input label="Username" name="username" autoComplete="username" required />
          <Input
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
          <SubmitButton className="w-full">Continue</SubmitButton>
        </form>
      </div>
    </div>
  );
}
