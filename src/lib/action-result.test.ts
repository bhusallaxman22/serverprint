import { describe, expect, it } from "vitest";
import { errorMessage, fail, ok } from "@/lib/action-result";

describe("action-result", () => {
  it("builds success and failure results", () => {
    expect(ok()).toEqual({ ok: true });
    expect(ok("Saved")).toEqual({ ok: true, message: "Saved" });
    expect(fail("Nope")).toEqual({ ok: false, error: "Nope" });
  });

  it("extracts error messages safely", () => {
    expect(errorMessage(new Error("boom"))).toBe("boom");
    expect(errorMessage("plain")).toBe("plain");
    expect(errorMessage(null)).toBe("Something went wrong.");
  });
});
