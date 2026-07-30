import path from "node:path";

function env(name: string, fallback?: string): string {
  const value = process.env[name] ?? fallback;
  if (value === undefined) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function envBool(name: string, fallback: boolean): boolean {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  return ["1", "true", "yes", "on"].includes(raw.toLowerCase());
}

function envInt(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

export const config = {
  appName: "PrintDrop",
  environment: process.env.NODE_ENV ?? "production",
  tz: process.env.TZ ?? "UTC",
  databaseUrl: env("DATABASE_URL", "file:./prisma/dev.db"),
  sessionSecret: env("SESSION_SECRET", "change-me-session-secret-min-32-chars!!"),
  printApiKey: env("PRINT_API_KEY", "change-me"),
  adminUsername: process.env.ADMIN_USERNAME ?? "admin",
  adminPassword: process.env.ADMIN_PASSWORD ?? "admin123456",
  cupsServer: process.env.CUPS_SERVER ?? "cups",
  printerName: process.env.PRINTER_NAME ?? "HP_LaserJet_M15w",
  maxUploadMb: envInt("MAX_UPLOAD_MB", 20),
  secureCookies: envBool("SECURE_COOKIES", false),
  cookieSameSite: (process.env.COOKIE_SAMESITE ?? "lax") as "lax" | "strict" | "none",
  printStatusPollSeconds: envInt("PRINT_STATUS_POLL_SECONDS", 30),
  failedFileRetentionHours: envInt("FAILED_FILE_RETENTION_HOURS", 72),
  pendingFileRetentionDays: envInt("PENDING_FILE_RETENTION_DAYS", 14),
  sessionMaxAgeSeconds: envInt("SESSION_MAX_AGE_SECONDS", 60 * 60 * 8),
  loginRateLimitPerMinute: envInt("LOGIN_RATE_LIMIT_PER_MINUTE", 12),
  uploadRateLimitPerMinute: envInt("UPLOAD_RATE_LIMIT_PER_MINUTE", 30),
  uploadsRoot: path.resolve(process.env.UPLOADS_ROOT ?? "./data/uploads"),
  tmpRoot: path.resolve(process.env.TMP_ROOT ?? "./data/tmp"),
  retainSuccessfulUploads: envBool("RETAIN_SUCCESSFUL_UPLOADS", false),
  forcePasswordChangeDefault: envBool("FORCE_PASSWORD_CHANGE_DEFAULT", true),
  runScheduler: envBool("RUN_SCHEDULER", false),
  webPort: envInt("PORT", 8000),
  allowFailedJobRetry: envBool("ALLOW_FAILED_JOB_RETRY", true),
  maxJobRetries: envInt("MAX_JOB_RETRIES", 3),
  get maxUploadBytes() {
    return this.maxUploadMb * 1024 * 1024;
  },
};

export type AppConfig = typeof config;
