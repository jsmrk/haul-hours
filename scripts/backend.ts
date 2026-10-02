import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

export const root = fileURLToPath(new URL("../", import.meta.url));
export const python = process.env["HAUL_HOURS_PYTHON"] ?? resolve(root, "backend/.venv/bin/python");

export function runBackend(args: readonly string[], environment: NodeJS.ProcessEnv = {}): Promise<number> {
  return new Promise((done, reject) => {
    const child = spawn(python, [...args], { cwd: resolve(root, "backend"), stdio: "inherit", env: { ...process.env, ...environment } });
    const stop = (signal: NodeJS.Signals) => child.kill(signal);
    const interrupt = () => stop("SIGINT");
    const terminate = () => stop("SIGTERM");
    process.on("SIGINT", interrupt);
    process.on("SIGTERM", terminate);
    child.on("error", reject);
    child.on("exit", (code) => {
      process.off("SIGINT", interrupt);
      process.off("SIGTERM", terminate);
      done(code ?? 1);
    });
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const actions: Record<string, string[]> = {
    dev: ["manage.py", "runserver", `127.0.0.1:${process.env["HAUL_HOURS_API_PORT"] ?? "8000"}`],
    demo: ["manage.py", "runserver", `127.0.0.1:${process.env["HAUL_HOURS_API_PORT"] ?? "8000"}`],
    test: ["-m", "pytest", "-q", ...process.argv.slice(3)],
    check: ["manage.py", "check"],
    lint: ["-m", "ruff", "check", "."],
  };
  const args = actions[process.argv[2] ?? ""];
  if (!args) throw new Error("Use dev, test, check, or lint");
  process.exitCode = await runBackend(args, process.argv[2] === "demo" ? { DJANGO_DEBUG: "true", PROVIDER_MODE: "fixtures" } : {});
}
