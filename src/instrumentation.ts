import { bootstrapAdmin } from "@/lib/services/bootstrap";
import { startBackgroundScheduler } from "@/lib/services/scheduler";
import { config } from "@/lib/config";
import fs from "node:fs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    fs.mkdirSync(config.uploadsRoot, { recursive: true });
    fs.mkdirSync(config.tmpRoot, { recursive: true });
    await bootstrapAdmin();
    startBackgroundScheduler();
  }
}
