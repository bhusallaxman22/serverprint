import { describe, expect, it } from "vitest";
import { QuotaService } from "@/lib/services/quota";

describe("QuotaService period boundaries", () => {
  it("computes usage without throwing for UTC", async () => {
    const service = new QuotaService("UTC");
    const fakeDb = {
      printJob: {
        findMany: async () => [
          { pageCount: 2, copies: 3, submittedAt: new Date() },
          {
            pageCount: 1,
            copies: 1,
            submittedAt: new Date(Date.now() - 8 * 86400000),
          },
        ],
      },
    };
    const usage = await service.getUsageForUser(
      fakeDb as never,
      {
        id: 1,
        dailyPageQuota: 250,
        weeklyPageQuota: 1000,
      } as never,
    );
    expect(usage.dailyUsed).toBe(6);
    expect(usage.weeklyUsed).toBeGreaterThanOrEqual(6);
  });
});
