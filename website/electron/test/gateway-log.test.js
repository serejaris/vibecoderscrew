// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");

const { createGatewayLogger } = require("../gateway-log");

class BrokenStream extends EventEmitter {
  constructor(code) {
    super();
    this.code = code;
    this.destroyed = false;
    this.writable = true;
    this.writeCalls = 0;
  }

  write() {
    this.writeCalls += 1;
    const err = Object.assign(new Error(`write ${this.code}`), { code: this.code });
    this.destroyed = true;
    queueMicrotask(() => this.emit("error", err));
    throw err;
  }
}

test("logger survives synchronous stdout EIO and asynchronous stream error", async () => {
  const stdout = new BrokenStream("EIO");
  const entries = [];
  const logger = createGatewayLogger({
    getLogPath: () => "/tmp/gateway-launch.log",
    appendFileSync: (_path, entry) => entries.push(entry),
    stdout,
    stderr: null,
    now: () => 0,
  });

  assert.doesNotThrow(() => logger.log("closed stdout"));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(stdout.writeCalls, 1);
  assert.equal(entries.length, 1);
  assert.match(entries[0], /closed stdout/);
  logger.dispose();
});

test("logger survives synchronous stderr EPIPE and keeps file diagnostics", async () => {
  const stderr = new BrokenStream("EPIPE");
  const entries = [];
  const logger = createGatewayLogger({
    getLogPath: () => "/tmp/gateway-launch.log",
    appendFileSync: (_path, entry) => entries.push(entry),
    stdout: null,
    stderr,
    now: () => 0,
  });

  assert.doesNotThrow(() => logger.error("closed stderr"));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(stderr.writeCalls, 1);
  assert.equal(entries.length, 1);
  assert.match(entries[0], /closed stderr/);
  logger.dispose();
});

test("logger skips destroyed or non-writable streams without throwing", () => {
  const destroyed = { destroyed: true, writable: true, write: () => { throw new Error("must not write"); } };
  const closed = { destroyed: false, writable: false, write: () => { throw new Error("must not write"); } };
  const entries = [];
  const logger = createGatewayLogger({
    getLogPath: () => "/tmp/gateway-launch.log",
    appendFileSync: (_path, entry) => entries.push(entry),
    stdout: destroyed,
    stderr: closed,
    now: () => 0,
  });

  assert.doesNotThrow(() => logger.log("destroyed"));
  assert.doesNotThrow(() => logger.error("closed"));
  assert.equal(entries.length, 2);
  logger.dispose();
});
