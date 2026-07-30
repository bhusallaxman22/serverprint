import { bootstrapAdmin } from "@/lib/services/bootstrap";
import { startBackgroundScheduler } from "@/lib/services/scheduler";
import { config } from "@/lib/config";
import fs from "node:fs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    fs.mkdirSync(config.uploadsRoot, { recursive: true });
    fs.mkdirSync(config.tmpRoot, { recursive: true });
    try {
      await bootstrapAdmin();
    } catch (error) {
      // Bootstrap is idempotent and swallows expected duplicates; log unexpected
      // failures without failing the instrumentation hook / taking down the app.
      console.error("bootstrapAdmin failed during instrumentation", error);
    }
    startBackgroundScheduler();
  }
}
