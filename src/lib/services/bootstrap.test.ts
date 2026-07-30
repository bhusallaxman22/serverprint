import { beforeEach, describe, expect, it, vi } from "vitest";
import { Prisma } from "@prisma/client";

const findFirst = vi.fn();
const create = vi.fn();

vi.mock("@/lib/db/prisma", () => ({
  prisma: {
    user: {
      findFirst: (...args: unknown[]) => findFirst(...args),
      create: (...args: unknown[]) => create(...args),
    },
  },
}));

vi.mock("@/lib/auth/password", () => ({
  hashPassword: vi.fn(async () => "hashed-password"),
}));

vi.mock("@/lib/config", () => ({
  config: {
    adminUsername: "admin",
    adminPassword: "not-the-default-password",
    forcePasswordChangeDefault: true,
  },
}));

function uniqueConstraintError() {
  return new Prisma.PrismaClientKnownRequestError("Unique constraint failed", {
    code: "P2002",
    clientVersion: "test",
    meta: { target: ["username"] },
  });
}

describe("bootstrapAdmin", () => {
  beforeEach(() => {
    findFirst.mockReset();
    create.mockReset();
  });

  it("no-ops when an admin (or reserved username) already exists", async () => {
    findFirst.mockResolvedValue({ id: 1 });
    const { bootstrapAdmin } = await import("@/lib/services/bootstrap");
    await expect(bootstrapAdmin()).resolves.toBeUndefined();
    expect(create).not.toHaveBeenCalled();
  });

  it("creates the admin when none exists", async () => {
    findFirst.mockResolvedValue(null);
    create.mockResolvedValue({ id: 1 });
    const { bootstrapAdmin } = await import("@/lib/services/bootstrap");
    await expect(bootstrapAdmin()).resolves.toBeUndefined();
    expect(create).toHaveBeenCalledOnce();
    const data = create.mock.calls[0][0].data;
    expect(data.username).toBe("admin");
    expect(data.usernameNormalized).toBe("admin");
    expect(data.passwordHash).toBe("hashed-password");
    expect(data.role).toBe("admin");
  });

  it("treats P2002 as success (race / already exists)", async () => {
    findFirst.mockResolvedValue(null);
    create.mockRejectedValue(uniqueConstraintError());
    const { bootstrapAdmin } = await import("@/lib/services/bootstrap");
    await expect(bootstrapAdmin()).resolves.toBeUndefined();
  });

  it("survives concurrent double-invoke without throwing", async () => {
    findFirst.mockResolvedValue(null);
    let creates = 0;
    create.mockImplementation(async () => {
      creates += 1;
      if (creates === 1) return { id: 1 };
      throw uniqueConstraintError();
    });
    const { bootstrapAdmin } = await import("@/lib/services/bootstrap");
    await expect(Promise.all([bootstrapAdmin(), bootstrapAdmin()])).resolves.toEqual([
      undefined,
      undefined,
    ]);
    expect(create).toHaveBeenCalledTimes(2);
  });

  it("rethrows unexpected create errors", async () => {
    findFirst.mockResolvedValue(null);
    create.mockRejectedValue(new Error("db down"));
    const { bootstrapAdmin } = await import("@/lib/services/bootstrap");
    await expect(bootstrapAdmin()).rejects.toThrow("db down");
  });
});
