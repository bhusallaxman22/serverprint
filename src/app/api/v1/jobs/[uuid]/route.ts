import { NextResponse } from "next/server";
import { prisma } from "@/lib/db/prisma";
import { getCurrentUser } from "@/lib/auth/guards";
import { requirePrintApiKey } from "@/lib/auth/guards";
import { config } from "@/lib/config";
import { serializeJob } from "@/lib/security";

type Params = { params: Promise<{ uuid: string }> };

export async function GET(request: Request, { params }: Params) {
  const { uuid } = await params;
  const apiKey =
    request.headers.get("x-print-api-key") ??
    request.headers.get("authorization")?.replace(/^Bearer\s+/i, "") ??
    null;
  const user = await getCurrentUser();
  const apiOk = requirePrintApiKey(apiKey, config.printApiKey);
  if (!user && !apiOk) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const job = await prisma.printJob.findUnique({ where: { jobUuid: uuid } });
  if (!job) {
    return NextResponse.json({ detail: "Job not found." }, { status: 404 });
  }
  if (user && user.role !== "admin" && job.userId !== user.id && !apiOk) {
    return NextResponse.json({ detail: "Job not found." }, { status: 404 });
  }
  return NextResponse.json(serializeJob(job));
}
