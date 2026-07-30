import { describe, expect, it } from "vitest";
import { DocumentValidationError, validateDocument } from "@/lib/services/document";
import { allowRateLimit } from "@/lib/services/rate-limit";
import { constantTimeEquals } from "@/lib/security";

describe("validateDocument", () => {
  it("accepts a minimal PDF and counts pages", async () => {
    // Minimal valid-ish PDF with one page object isn't required — pdf-lib can create one.
    const { PDFDocument } = await import("pdf-lib");
    const doc = await PDFDocument.create();
    doc.addPage();
    const bytes = Buffer.from(await doc.save());
    const meta = await validateDocument("test.pdf", "application/pdf", bytes);
    expect(meta.mimeType).toBe("application/pdf");
    expect(meta.pageCount).toBe(1);
    expect(meta.extension).toBe(".pdf");
  });

  it("rejects unsupported extensions", async () => {
    await expect(validateDocument("x.txt", "text/plain", Buffer.from("hi"))).rejects.toBeInstanceOf(
      DocumentValidationError,
    );
  });

  it("rejects mime/signature mismatch", async () => {
    const png = Buffer.concat([
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
      Buffer.from("not-a-real-png-but-signature"),
    ]);
    await expect(
      validateDocument("x.png", "application/pdf", png),
    ).rejects.toBeInstanceOf(DocumentValidationError);
  });
});

describe("constantTimeEquals", () => {
  it("compares equal strings", () => {
    expect(constantTimeEquals("abc", "abc")).toBe(true);
    expect(constantTimeEquals("abc", "abd")).toBe(false);
    expect(constantTimeEquals("a", "aa")).toBe(false);
  });
});

describe("allowRateLimit", () => {
  it("allows until limit then blocks", () => {
    const key = `test-${Math.random()}`;
    expect(allowRateLimit(key, { limit: 2, windowSeconds: 60 })).toBe(true);
    expect(allowRateLimit(key, { limit: 2, windowSeconds: 60 })).toBe(true);
    expect(allowRateLimit(key, { limit: 2, windowSeconds: 60 })).toBe(false);
  });
});

describe("CUPSService", () => {
  it("exposes printerName for status snapshots", async () => {
    const { CUPSService } = await import("@/lib/services/cups");
    const cups = new CUPSService("cups.local", "HP_LaserJet_M15w");
    expect(cups.printerName).toBe("HP_LaserJet_M15w");
  });
});
