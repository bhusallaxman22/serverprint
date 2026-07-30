import { spawn } from "node:child_process";
import type { PathLike } from "node:fs";

export class CUPSServiceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CUPSServiceError";
  }
}

export type CUPSJobState = {
  cupsJobId: string;
  state: string;
};

function runCommand(
  command: string,
  args: string[],
  env: NodeJS.ProcessEnv,
): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf8");
    });
    child.on("error", reject);
    child.on("close", (code) => {
      resolve({ code: code ?? 1, stdout, stderr });
    });
  });
}

export class CUPSService {
  readonly printerName: string;

  constructor(
    private readonly cupsServer: string,
    printerName: string,
  ) {
    this.printerName = printerName;
  }

  private commandEnv(): NodeJS.ProcessEnv {
    return { ...process.env, CUPS_SERVER: this.cupsServer };
  }

  async submitJob(filePath: PathLike, title: string, copies: number): Promise<string> {
    const result = await runCommand(
      "lp",
      [
        "-h",
        this.cupsServer,
        "-d",
        this.printerName,
        "-n",
        String(copies),
        "-t",
        title,
        String(filePath),
      ],
      this.commandEnv(),
    );
    if (result.code !== 0) {
      throw new CUPSServiceError("Failed to queue print job.");
    }
    const match = /request id is [^-]+-(\d+)/.exec(result.stdout);
    if (!match) {
      throw new CUPSServiceError("Failed to parse CUPS job id.");
    }
    return match[1];
  }

  async fetchJobStates(): Promise<CUPSJobState[] | null> {
    const result = await runCommand(
      "lpstat",
      ["-h", this.cupsServer, "-W", "not-completed", "-o", this.printerName],
      this.commandEnv(),
    );
    if (result.code !== 0) return null;

    const states: CUPSJobState[] = [];
    const re = new RegExp(`^${escapeRegExp(this.printerName)}-(\\d+)\\s+`);
    for (const line of result.stdout.split("\n")) {
      const match = re.exec(line);
      if (match) {
        states.push({ cupsJobId: match[1], state: "active" });
      }
    }
    return states;
  }

  async cancelCupsJob(cupsJobId: string): Promise<void> {
    await runCommand(
      "cancel",
      ["-h", this.cupsServer, `${this.printerName}-${cupsJobId}`],
      this.commandEnv(),
    );
  }

  async checkPrinterReachability(): Promise<{ reachable: boolean; reason: string | null }> {
    const result = await runCommand(
      "lpstat",
      ["-h", this.cupsServer, "-p", this.printerName],
      this.commandEnv(),
    );
    if (result.code !== 0) {
      return { reachable: false, reason: "CUPS command failed." };
    }
    const output = result.stdout.trim().toLowerCase();
    if (output.includes("disabled") || output.includes("not accepting requests")) {
      return { reachable: false, reason: "Printer is not accepting jobs." };
    }
    return { reachable: true, reason: null };
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
