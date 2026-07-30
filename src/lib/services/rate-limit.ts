type RateLimitRule = {
  limit: number;
  windowSeconds: number;
};

type Bucket = {
  count: number;
  resetAt: number;
};

const buckets = new Map<string, Bucket>();

export function allowRateLimit(key: string, rule: RateLimitRule): boolean {
  const now = Date.now();
  const existing = buckets.get(key);
  if (!existing || existing.resetAt <= now) {
    buckets.set(key, { count: 1, resetAt: now + rule.windowSeconds * 1000 });
    return true;
  }
  if (existing.count >= rule.limit) return false;
  existing.count += 1;
  return true;
}
