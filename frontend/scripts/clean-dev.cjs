const { execFileSync, spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const frontendRoot = path.resolve(__dirname, "..");
const frontendRootLower = frontendRoot.toLowerCase();
const ports = [3000, 3001, 3002];
const backendHealthUrl = process.env.BACKEND_HEALTH_URL || "http://127.0.0.1:8000/api/v1/health";

function run(command, args, options = {}) {
  return execFileSync(command, args, {
    encoding: "utf8",
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  });
}

function listPortOwners() {
  const output = run("netstat.exe", ["-ano", "-p", "tcp"]);
  const owners = new Map();

  for (const line of output.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("TCP")) continue;

    const parts = trimmed.split(/\s+/);
    const localAddress = parts[1] || "";
    const state = parts[3] || "";
    const pid = Number(parts[4]);
    const match = localAddress.match(/:(\d+)$/);
    if (!match || state !== "LISTENING" || !Number.isInteger(pid)) continue;

    const port = Number(match[1]);
    if (ports.includes(port)) {
      if (!owners.has(port)) owners.set(port, new Set());
      owners.get(port).add(pid);
    }
  }

  return owners;
}

function getProcessInfo(pid) {
  try {
    const output = run("wmic.exe", [
      "process",
      "where",
      `ProcessId=${pid}`,
      "get",
      "ProcessId,ParentProcessId,CommandLine",
      "/format:list",
    ]);
    const info = {};
    for (const line of output.split(/\r?\n/)) {
      const index = line.indexOf("=");
      if (index <= 0) continue;
      info[line.slice(0, index)] = line.slice(index + 1).trim();
    }
    return {
      pid,
      parentPid: Number(info.ParentProcessId) || undefined,
      commandLine: info.CommandLine || "",
    };
  } catch {
    return { pid, commandLine: "" };
  }
}

function isFrontendDevProcess(info) {
  const command = info.commandLine.toLowerCase();
  return (
    command.includes(frontendRootLower) ||
    command.includes("node_modules\\next") ||
    command.includes("node_modules/next") ||
    command.includes("next dev") ||
    command.includes("npm-cli.js") ||
    command.includes("npm.cmd run dev")
  );
}

function getProcessChain(pid) {
  const chain = [];
  const seen = new Set();
  let currentPid = pid;

  while (currentPid && !seen.has(currentPid) && chain.length < 8) {
    seen.add(currentPid);
    const info = getProcessInfo(currentPid);
    chain.push(info);
    currentPid = info.parentPid;
  }

  return chain;
}

function getFrontendDevTreeRoot(pid) {
  const chain = getProcessChain(pid).filter(isFrontendDevProcess);
  return chain.length ? chain[chain.length - 1] : undefined;
}

function wait(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function terminateFrontendPortOwners() {
  const owners = listPortOwners();
  const terminatedPids = new Set();
  if (!owners.size) {
    console.log("[clean-dev] Ports 3000-3002 are free.");
    return;
  }

  for (const [port, pids] of owners.entries()) {
    for (const pid of pids) {
      const root = getFrontendDevTreeRoot(pid);
      if (!root) {
        console.log(`[clean-dev] Port ${port} is occupied by PID ${pid}; leaving it alone because it is not this frontend dev server.`);
        continue;
      }
      if (terminatedPids.has(root.pid)) continue;

      terminatedPids.add(root.pid);
      console.log(`[clean-dev] Stopping stale frontend dev process tree PID ${root.pid} on port ${port}.`);
      try {
        process.kill(root.pid, "SIGTERM");
      } catch {
        // The process may have already exited.
      }
    }
  }

  wait(1500);

  for (const [port, pids] of listPortOwners().entries()) {
    for (const pid of pids) {
      const root = getFrontendDevTreeRoot(pid);
      if (!root) continue;
      console.log(`[clean-dev] Force-stopping unresponsive frontend dev process tree PID ${root.pid} on port ${port}.`);
      run("taskkill.exe", ["/PID", String(root.pid), "/T", "/F"], { stdio: ["ignore", "ignore", "ignore"] });
    }
  }
}

function clearNextCache() {
  const nextDir = path.resolve(frontendRoot, ".next");
  if (!nextDir.toLowerCase().startsWith(frontendRootLower)) {
    throw new Error(`Refusing to delete outside frontend root: ${nextDir}`);
  }
  fs.rmSync(nextDir, { recursive: true, force: true });
  console.log("[clean-dev] Cleared generated Next.js cache.");
}

function checkBackendHealth() {
  return new Promise((resolve) => {
    const request = http.get(backendHealthUrl, { timeout: 30_000 }, (response) => {
      response.resume();
      resolve(response.statusCode && response.statusCode >= 200 && response.statusCode < 500);
    });

    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

function appendNodeOption(current, optionPrefix, optionValue) {
  if (current.split(/\s+/).some((item) => item.startsWith(optionPrefix))) return current;
  return `${current} ${optionValue}`.trim();
}

async function main() {
  console.log("[clean-dev] Frontend root:", frontendRoot);
  console.log("[clean-dev] Baseline script heap:", Math.round(process.memoryUsage().rss / 1024 / 1024), "MB RSS");

  terminateFrontendPortOwners();
  clearNextCache();

  const backendHealthy = await checkBackendHealth();
  console.log(backendHealthy ? "[clean-dev] Backend health check responded." : "[clean-dev] Backend health check did not respond; frontend will still start.");

  const env = { ...process.env };
  env.NODE_OPTIONS = appendNodeOption(env.NODE_OPTIONS || "", "--max-old-space-size", "--max-old-space-size=4096");
  env.NODE_OPTIONS = appendNodeOption(env.NODE_OPTIONS || "", "--max-semi-space-size", "--max-semi-space-size=128");
  env.NEXT_TELEMETRY_DISABLED = env.NEXT_TELEMETRY_DISABLED || "1";

  console.log("[clean-dev] Starting Next.js dev server.");
  const command = process.platform === "win32" ? process.env.ComSpec || "cmd.exe" : "npm";
  const args = process.platform === "win32" ? ["/c", "npm.cmd", "run", "dev:next"] : ["run", "dev:next"];
  const child = spawn(command, args, {
    cwd: frontendRoot,
    env,
    stdio: "inherit",
    windowsHide: false,
  });

  child.on("exit", (code, signal) => {
    if (signal) process.kill(process.pid, signal);
    process.exit(code || 0);
  });
}

main().catch((error) => {
  console.error("[clean-dev] Startup failed:", error);
  process.exit(1);
});
