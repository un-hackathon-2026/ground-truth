import { spawn } from "child_process";
import path from "path";
import fs from "fs";

export const PROJECT_ROOT = path.resolve(process.cwd(), "..");

function loadDotEnv(dir: string): Record<string, string> {
  const env: Record<string, string> = {};
  try {
    const raw = fs.readFileSync(path.join(dir, ".env"), "utf-8");
    for (const line of raw.split("\n")) {
      const t = line.trim();
      if (!t || t.startsWith("#")) continue;
      const eq = t.indexOf("=");
      if (eq < 0) continue;
      const k = t.slice(0, eq).trim();
      let v = t.slice(eq + 1).trim();
      if (
        (v.startsWith('"') && v.endsWith('"')) ||
        (v.startsWith("'") && v.endsWith("'"))
      ) {
        v = v.slice(1, -1);
      }
      env[k] = v;
    }
  } catch {
    // no .env — fine
  }
  return env;
}

export function runPython(
  module: string,
  stdinPayload: unknown,
  timeoutMs = 90_000
): Promise<string> {
  const extraEnv = loadDotEnv(PROJECT_ROOT);

  return new Promise((resolve, reject) => {
    const proc = spawn("python3", ["-X", "utf8", "-m", module], {
      cwd: PROJECT_ROOT,
      env: { ...process.env, ...extraEnv, PYTHONUNBUFFERED: "1" },
    });

    let stdout = "";
    let stderr = "";

    proc.stdin.write(JSON.stringify(stdinPayload));
    proc.stdin.end();

    proc.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf8");
    });
    proc.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf8");
    });

    const timer = setTimeout(() => {
      proc.kill();
      reject(new Error("Pipeline timed out after 90s"));
    }, timeoutMs);

    proc.on("close", (code) => {
      clearTimeout(timer);
      if (!stdout && code !== 0) {
        reject(new Error(stderr.trim() || `Process exited with code ${code}`));
      } else {
        resolve(stdout);
      }
    });

    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}
