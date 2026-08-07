// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
// Fault-tolerant gateway diagnostics. LaunchServices may give Electron a
// stdout/stderr stream whose peer has already gone away. Logging must remain a
// best-effort side effect in that situation: the file record is useful, while
// a console EIO/EPIPE must never become an uncaught exception in the app.
const fs = require("fs");

function streamCanWrite(stream) {
  if (!stream) return false;
  try {
    return stream.destroyed !== true && stream.writable !== false;
  } catch {
    return false;
  }
}

function createGatewayLogger({
  getLogPath,
  appendFileSync = fs.appendFileSync,
  stdout = process.stdout,
  stderr = process.stderr,
  now = () => Date.now(),
} = {}) {
  const errorListeners = [];
  const streams = [stdout, stderr].filter(Boolean);

  // A Writable can emit EPIPE/EIO asynchronously after write() returned. A
  // no-op listener prevents Node's EventEmitter default (throwing an
  // unhandled 'error') while preserving the primary file diagnostic.
  for (const stream of streams) {
    if (typeof stream.on !== "function") continue;
    const onError = () => {};
    try {
      stream.on("error", onError);
      errorListeners.push([stream, onError]);
    } catch { /* a hostile/closed stream is simply unavailable */ }
  }

  function writeConsole(stream, text) {
    if (!streamCanWrite(stream) || typeof stream.write !== "function") return;
    try { stream.write(text); } catch { /* EPIPE/EIO must never escape logging */ }
  }

  function record(line, stream) {
    let stamp;
    try { stamp = new Date(now()).toISOString(); } catch { stamp = new Date().toISOString(); }
    const entry = `[${stamp}] ${line}\n`;
    try {
      const logPath = typeof getLogPath === "function" ? getLogPath() : "";
      if (logPath) appendFileSync(logPath, entry);
    } catch { /* diagnostics are best effort and must not break launch */ }
    writeConsole(stream, `[gateway-launch] ${line}\n`);
  }

  function dispose() {
    for (const [stream, listener] of errorListeners.splice(0)) {
      try {
        if (typeof stream.off === "function") stream.off("error", listener);
        else if (typeof stream.removeListener === "function") stream.removeListener("error", listener);
      } catch { /* stream teardown is also best effort */ }
    }
  }

  return {
    log: (line) => record(line, stdout),
    error: (line) => record(line, stderr),
    dispose,
  };
}

module.exports = { createGatewayLogger };
