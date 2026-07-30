import {
  type Prisma,
  type PrismaClient,
  PrintJobStatus,
  type User,
} from "@prisma/client";

const ACTIVE_QUOTA_STATUSES: PrintJobStatus[] = [
  PrintJobStatus.pending,
  PrintJobStatus.approved,
  PrintJobStatus.queued,
  PrintJobStatus.printing,
  PrintJobStatus.completed,
];

export class QuotaExceededError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "QuotaExceededError";
  }
}

export type QuotaUsage = {
  dailyUsed: number;
  weeklyUsed: number;
};

type DbClient = PrismaClient | Prisma.TransactionClient;

export class QuotaService {
  constructor(private readonly timezoneName: string) {}

  async ensureQuotaForNewJob(
    db: DbClient,
    user: User,
    pagesRequested: number,
    nowUtc: Date,
  ): Promise<void> {
    const { dailyStartUtc, weeklyStartUtc } = this.periodStartsUtc(nowUtc);
    const usage = await this.getUsage(db, user.id, dailyStartUtc, weeklyStartUtc);

    if (usage.dailyUsed + pagesRequested > user.dailyPageQuota) {
      throw new QuotaExceededError("Daily page quota exceeded.");
    }
    if (usage.weeklyUsed + pagesRequested > user.weeklyPageQuota) {
      throw new QuotaExceededError("Weekly page quota exceeded.");
    }
  }

  async getUsageForUser(db: DbClient, user: User, nowUtc = new Date()): Promise<QuotaUsage> {
    const { dailyStartUtc, weeklyStartUtc } = this.periodStartsUtc(nowUtc);
    return this.getUsage(db, user.id, dailyStartUtc, weeklyStartUtc);
  }

  private periodStartsUtc(nowUtc: Date): { dailyStartUtc: Date; weeklyStartUtc: Date } {
    const local = toZonedParts(nowUtc, this.timezoneName);
    const dailyLocal = new Date(
      Date.UTC(local.year, local.month - 1, local.day, 0, 0, 0, 0),
    );
    // Convert local midnight back to UTC using offset approximation via Intl
    const dailyStartUtc = zonedLocalToUtc(
      local.year,
      local.month,
      local.day,
      0,
      0,
      0,
      this.timezoneName,
    );
    const weekday = (dailyLocal.getUTCDay() + 6) % 7; // Monday=0
    const weeklyStartUtc = zonedLocalToUtc(
      local.year,
      local.month,
      local.day - weekday,
      0,
      0,
      0,
      this.timezoneName,
    );
    return { dailyStartUtc, weeklyStartUtc };
  }

  private async getUsage(
    db: DbClient,
    userId: number,
    dailyStartUtc: Date,
    weeklyStartUtc: Date,
  ): Promise<QuotaUsage> {
    const jobs = await db.printJob.findMany({
      where: {
        userId,
        status: { in: ACTIVE_QUOTA_STATUSES },
        submittedAt: { gte: weeklyStartUtc },
      },
      select: { pageCount: true, copies: true, submittedAt: true },
    });

    let dailyUsed = 0;
    let weeklyUsed = 0;
    for (const job of jobs) {
      const pages = job.pageCount * job.copies;
      weeklyUsed += pages;
      if (job.submittedAt >= dailyStartUtc) dailyUsed += pages;
    }
    return { dailyUsed, weeklyUsed };
  }
}

function toZonedParts(date: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value ?? "0");
  return {
    year: get("year"),
    month: get("month"),
    day: get("day"),
    hour: get("hour") % 24,
    minute: get("minute"),
    second: get("second"),
  };
}

function zonedLocalToUtc(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
  second: number,
  timeZone: string,
): Date {
  // Handle day underflow/overflow from weekly start math
  const probe = new Date(Date.UTC(year, month - 1, day, hour, minute, second));
  const asLocal = toZonedParts(probe, timeZone);
  const asUtc = {
    year: probe.getUTCFullYear(),
    month: probe.getUTCMonth() + 1,
    day: probe.getUTCDate(),
    hour: probe.getUTCHours(),
    minute: probe.getUTCMinutes(),
    second: probe.getUTCSeconds(),
  };
  const localMs = Date.UTC(
    asLocal.year,
    asLocal.month - 1,
    asLocal.day,
    asLocal.hour,
    asLocal.minute,
    asLocal.second,
  );
  const utcMs = Date.UTC(
    asUtc.year,
    asUtc.month - 1,
    asUtc.day,
    asUtc.hour,
    asUtc.minute,
    asUtc.second,
  );
  const offset = localMs - utcMs;
  return new Date(
    Date.UTC(year, month - 1, day, hour, minute, second) - offset,
  );
}
