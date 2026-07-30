export type ActionResult =
  | { ok: true; message?: string }
  | { ok: false; error: string };

export function ok(message?: string): ActionResult {
  return message ? { ok: true, message } : { ok: true };
}

export function fail(error: string): ActionResult {
  return { ok: false, error };
}

export function errorMessage(err: unknown, fallback = "Something went wrong."): string {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === "string" && err) return err;
  return fallback;
}
