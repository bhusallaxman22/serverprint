import { NextResponse } from "next/server";
import path from "node:path";
import { mkdirSync } from "node:fs";
import { writeFile, unlink } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { config } from "@/lib/config";
import { prisma } from "@/lib/db/prisma";
import { requirePrintApiKey } from "@/lib/auth/guards";
import { serializeJob } from "@/lib/security";
import { validateDocument, DocumentValidationError } from "@/lib/services/document";
import { QuotaExceededError, QuotaService } from "@/lib/services/quota";
import { CUPSService } from "@/lib/services/cups";
import { approveJob, createPendingJob } from "@/lib/services/jobs";

export async function POST(request: Request) {
  const apiKey =
    request.headers.get("x-print-api-key") ??
    request.headers.get("authorization")?.replace(/^Bearer\s+/i, "") ??
    null;
  if (!requirePrintApiKey(apiKey, config.printApiKey)) {
    return NextResponse.json({ detail: "Invalid API key." }, { status: 401 });
  }

  const form = await request.formData();
  const username = String(form.get("username") ?? "").trim();
  const copies = Math.min(100, Math.max(1, Number(form.get("copies") ?? 1)));
  const file = form.get("file");

  if (!username) {
    return NextResponse.json({ detail: "username is required." }, { status: 400 });
  }
  if (!(file instanceof File)) {
    return NextResponse.json({ detail: "file is required." }, { status: 400 });
  }
  if (file.size > config.maxUploadBytes) {
    return NextResponse.json({ detail: "File too large." }, { status: 413 });
  }

  const user = await prisma.user.findUnique({
    where: { usernameNormalized: username.toLowerCase() },
  });
  if (!user || !user.isActive) {
    return NextResponse.json({ detail: "User not found." }, { status: 404 });
  }

  const content = Buffer.from(await file.arrayBuffer());
  let metadata;
  try {
    metadata = await validateDocument(file.name || "document", file.type, content);
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof DocumentValidationError ? err.message : "Invalid document." },
      { status: 400 },
    );
  }

  mkdirSync(config.uploadsRoot, { recursive: true });
  const storedFilename = `${randomUUID()}${path.extname(file.name || "document").toLowerCase()}`;
  const storedPath = path.join(config.uploadsRoot, storedFilename);
  await writeFile(storedPath, content);

  try {
    const job = await prisma.$transaction(async (tx) => {
      const pending = await createPendingJob(tx, {
        user,
        originalFilename: file.name || "document",
        storedFilename,
        metadata,
        copies,
        quotaService: new QuotaService(config.tz),
      });
      if (!user.requiresApproval) {
        return approveJob(tx, {
          actor: user,
          job: pending,
          cupsService: new CUPSService(config.cupsServer, config.printerName),
          filePath: storedPath,
        });
      }
      return pending;
    });
    return NextResponse.json(serializeJob(job), { status: 200 });
  } catch (err) {
    try {
      await unlink(storedPath);
    } catch {
      /* ignore */
    }
    if (err instanceof QuotaExceededError) {
      return NextResponse.json({ detail: err.message }, { status: 409 });
    }
    throw err;
  }
}
