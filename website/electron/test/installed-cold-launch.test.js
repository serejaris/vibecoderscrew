// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const APP_BINARY = "/Applications/VibecodersCrew.app/Contents/MacOS/VibecodersCrew";
const START_TIMEOUT_MS = 20_000;

function freePort() {
  return new Promise((resolve, reject) => {
    const server = http.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close((err) => (err ? reject(err) : resolve(port)));
    });
  });
}

function waitForHealth(port, child, output) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + START_TIMEOUT_MS;
    let timer;
    let settled = false;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      child.off("exit", onExit);
      fn(value);
    };
    const onExit = (code, signal) => {
      finish(reject, new Error(`installed app exited before health: code=${code} signal=${signal}\n${output()}`));
    };
    const probe = () => {
      if (settled) return;
      if (Date.now() >= deadline) {
        finish(reject, new Error(`installed app health timeout on :${port}\n${output()}`));
        return;
      }
      const req = http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
        res.resume();
        if (res.statusCode >= 200 && res.statusCode < 500) {
          finish(resolve);
        } else {
          req.once("close", () => { timer = setTimeout(probe, 100); });
        }
      });
      req.setTimeout(500, () => req.destroy());
      req.once("error", () => { timer = setTimeout(probe, 100); });
    };
    child.once("exit", onExit);
    probe();
  });
}

async function stopChild(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  child.kill("SIGTERM");
  await new Promise((resolve) => {
    const timeout = setTimeout(() => {
      if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
      resolve();
    }, 3_000);
    child.once("exit", () => { clearTimeout(timeout); resolve(); });
  });
}

test("installed app cold launch reaches the gateway with Finder-like PATH", { timeout: 30_000 }, async (t) => {
  if (process.platform !== "darwin" || !fs.existsSync(APP_BINARY)) {
    t.skip("macOS installed app is unavailable");
    return;
  }

  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vibecoderscrew-cold-launch-"));
  const home = path.join(root, "home");
  const kiroHome = path.join(root, "kiro");
  fs.mkdirSync(home, { recursive: true });
  fs.mkdirSync(kiroHome, { recursive: true, mode: 0o700 });
  const port = await freePort();
  fs.writeFileSync(path.join(kiroHome, "config.json"), JSON.stringify({
    agent: { provider: "codex" },
    dashboard: {
      url: `http://127.0.0.1:${port}`,
      auto_open_browser: false,
      onboarded: true,
      import_onboarded: true,
    },
  }));

  const child = spawn(APP_BINARY, [], {
    env: {
      ...process.env,
      HOME: home,
      USERPROFILE: home,
      KIROCREW_HOME: kiroHome,
      KIROCREW_PORT: String(port),
      PATH: "/usr/bin:/bin:/usr/sbin:/sbin",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
  child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
  const output = () => `stdout:\n${stdout}\nstderr:\n${stderr}`;
  try {
    await waitForHealth(port, child, output);
    assert.equal(child.exitCode, null, `app exited after health\n${output()}`);
  } finally {
    await stopChild(child);
    fs.rmSync(root, { recursive: true, force: true });
  }
});
