<!-- Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew). See NOTICE and CHANGELOG.md. -->
# Metrics Telemetry Module

> **VibecodersCrew policy:** all telemetry is hard-disabled. Metric call
> sites resolve to no-ops; heartbeat/install receipts, local JSONL collection,
> and OTLP export cannot be enabled by config or environment variables. The
> detailed implementation below is retained as an auditable upstream reference.

Last Updated: 2026-08-07 (hard-disabled outbound telemetry boundary)

## Overview

The upstream tree contains a local-first OpenTelemetry implementation
(Apache-2.0 / CNCF). This edition places a compile-time distribution gate ahead
of it. Every production call receives a no-op recorder; no metrics file is
written and no exporter is constructed.

Source: `src/kiro_crew/metrics/` — `schema.py`, `recorder.py`, `provider.py`,
`local_exporter.py`, `http_metrics.py`. Tests: `test/metrics/`.

## Components

| File | Purpose |
|------|---------|
| `schema.py` | Namespace constants (`NS_CORE = "kirocrew."`, `NS_GENAI = "gen_ai."`, `NS_APP_PREFIX = "app."`) + `validate_name` / `validate_attrs` / `redact` guardrails. Documents the low-cardinality contract. |
| `recorder.py` | `MetricsRecorder` — facade over the OTEL `Meter`. Every metric passes namespace + privacy guardrails BEFORE reaching an instrument. Instrument-cache creation is lock-guarded (atomic check-then-create). Best-effort: a telemetry failure never propagates to the caller. `meter=None` = no-op recorder. |
| `provider.py` | Hard distribution gate + process-global no-op recorder (`get_recorder()`) + graceful `shutdown()` / `reset_for_testing()`. The inherited reader construction remains reachable only from tests that explicitly replace the gate. |
| `local_exporter.py` | `JsonlMetricExporter` — appends one JSON line per export cycle to `<dir>/metrics-YYYY-MM-DD-<pid>.jsonl` (default dir `~/.kiro/crew/metrics`). Per-PID single-writer shards keep append + rotation lock-free, so concurrent exporters do not lose DELTA cycles. A private `.metrics.lock` serializes only retention sweeps; pruning skips canonical shards owned by live PIDs or modified within the safety window. **Bounded retention (rec #14):** shards rotate before an append exceeds `max_total_mb`; closed/expired shards are pruned directly by age and oldest-first size. Pruning is throttled to at most once per 300s and fully best-effort. Dir mode is 0o700, file mode 0o600, and nothing egresses the host. Declares DELTA `preferred_temporality` for Counter/UpDownCounter/Histogram so daily aggregation is an element-wise sum across cycles/PIDs. |
| `http_metrics.py` | Gateway HTTP observability (rec #1): `record_boot_to_ready()` (boot-to-ready histogram) + `make_route_latency_middleware()` (per-route latency, wired as the outermost middleware on both `start_dashboard`/`start_api_server`). Bounds `route_template` cardinality via `collect_route_templates()` (build-time snapshot) + `route_template()` (`__unknown__` fallback); clamps `method` to a fixed allowlist and `status_class` to `1xx`..`5xx`/`other`. Upgraded WebSocket connections and `text/event-stream` SSE responses are excluded because their handler elapsed time is connection/turn lifetime, not HTTP request latency. Best-effort — a telemetry failure never alters a response. |

## Guardrails (contract C4)

- **Namespace**: core callers must use `kirocrew.*` or `gen_ai.*`; app callers
  must use `app.<app_id>.*` and cannot spoof the core/gen_ai namespaces
  (`validate_name` raises `ValueError`, the recorder swallows it, nothing is
  recorded).
- **Privacy**: string attribute values pass `redact()` — AKIA/ASIA keys,
  `SecretAccessKey=`, private-key headers, 40+ char hex, JWT shapes,
  `password=`/`token=` patterns, base64-encoded credential variants, and a
  Shannon-entropy heuristic all yield `"[REDACTED]"`. The first-party
  `kiro_crew.security` scrubbers (`redact_credentials`,
  `redact_exfiltration_urls` — both return `(cleaned, warnings)` tuples) are
  also consulted. Long non-suspicious strings are truncated to
  `MAX_ATTR_VALUE_LEN` (128).
- **Cardinality**: metric names + attribute values must be low-cardinality
  constants; attribute count is capped at `MAX_ATTR_COUNT` (32). Instrument
  caches are keyed by name and never evicted.

## Configuration

`TelemetryConfig` in `config/loader.py` (section `telemetry` in
`~/.kiro/crew/config.json`):

| Field | Default | Meaning |
|-------|---------|---------|
| `enabled` | `false` | Legacy field. `true` is rejected by supported CLI/API config paths and ignored by the production gate. |
| `local_dir` | `""` | Legacy path field; no file is created. |
| `export_interval_seconds` | `60` | Legacy reader setting; no reader is created. |
| `retention_days` | `0` | Legacy retention field; no telemetry storage is active. |
| `max_total_mb` | `0` | Legacy retention field; no telemetry storage is active. |
| `otlp_endpoint` | `""` | Legacy exporter field. Non-empty values are rejected by supported CLI/API config paths and ignored by the production gate. |

Field validation (`TelemetryConfig.__post_init__`): `export_interval_seconds`
below 1 is floored to 1; negative `retention_days` / `max_total_mb` are clamped
to `0` (cap disabled) rather than being interpreted as "prune everything".

## Distribution gate and egress

`PRODUCT_TELEMETRY_ENABLED = false` is the edition boundary. It wins over
`telemetry.enabled`, `KIROCREW_TELEMETRY`, and `otlp_endpoint`. The CLI and
dashboard also reject attempts to enable collection or configure OTLP. The
heartbeat beacon and install receipts use a separate
`OUTBOUND_TELEMETRY_ENABLED = false` boundary. Electron performance recording
uses the same hard-disabled distribution pattern. Automated tests temporarily
replace these constants only to keep the inherited implementation auditable.

## Inherited retention implementation reference (test-only)

The following describes the upstream exporter retained for compatibility tests.
It is unreachable in the production edition because the distribution gate
returns a no-op recorder before an exporter can be constructed. The retention
details therefore document test seams and historical files; they are not
operator configuration instructions.

**Bounded local retention (rec #14, upstream reference):** both destructive caps
default to `0`, so upgrading cannot delete existing telemetry history. A test
that explicitly replaces the production gate can exercise age and size bounds:
- *Age cap* — set `retention_days` to a positive window (for example `7`); shards
  whose mtime is older than that window are eligible for deletion.
- *Total-size cap* — set `max_total_mb` to a positive budget (for example `128`);
  before an append would
  exceed the live-shard budget, the exporter rotates that shard and opens a
  fresh canonical writer. Closed shards are then deleted oldest-first until the
  combined size is under budget. The active writer is retained; with
  multiple process-local writers, enforcement remains opportunistic rather than
  a strict instantaneous directory-wide byte ceiling. In the worst case, live
  protected shards can temporarily approach the number of active writers times
  `max_total_mb` before those writers rotate and closed shards become eligible
  for oldest-first deletion.
- *Both caps are independently configurable in that test-only path* and can be
  disabled again by setting the value to `0`.
- After a test enables a cap, before the first destructive plan in each
  exporter process, retention emits
  one fixed, path-free warning and defers deletion for a full 300-second prune
  interval. The test can set either cap to `0` during that window. The notice
  is process-local; there is no persistent migration marker or format to carry
  into future releases.
- Per-PID append + rotation are lock-free. A private cross-process
  `.metrics.lock` serializes only prune sweeps; contention skips pruning but
  never discards the DELTA payload already appended. Canonical shards owned by
  live PIDs or modified within the 300-second safety window are not deleted.
- Pruning is throttled (≤ once per 300s), runs only AFTER a successful append,
  and considers only regular files matching the exact generated grammar
  `metrics-YYYY-MM-DD-PID[-ROTATION_NS].jsonl`; broad-prefix lookalikes, invalid
  dates, symlinks, and the lock sidecar are excluded. It is fully best-effort —
  a rotation/prune failure is logged and swallowed, never breaking export.

**Never recorded:** prompts, message/tool content, token counts, filesystem
paths, user ids, and secrets. `telemetry.otlp_endpoint` is schema-sensitive so
credential-bearing collector URLs are masked by config API/UI consumers as well
as omitted from logs. Enforced structurally at the `MetricsRecorder`
facade via the `schema.py` guardrails (see below) — call sites emit only
low-cardinality enum-like attribute values, and any string that looks like a
credential/PII is redacted to `"[REDACTED]"` before it reaches an instrument.

Tests that explicitly replace the gate: `test/metrics/test_local_exporter.py`
(retention: direct age cap,
oldest-first size cap, live-writer protection, live-shard rotation, non-blocking
prune lock, append survives prune contention, both-disabled,
broad-prefix/malformed shard lookalikes ignored, export-then-prune never raises),
`test/metrics/test_provider.py` (default hard-disabled gate, explicit test seam,
OTLP reader construction under that seam, degrade when the extra is missing),
`test/metrics/test_schema.py` (redaction / namespace).

## Instrumented signals

| Metric | Type | Attrs | Site |
|--------|------|-------|------|
| `kirocrew.session.startup.duration` | histogram (ms) | `outcome` (`ready` / `auth_required` / `error`), `spawned` (bool), `backend` (`kiro`) + `phase` (`total` / `spawn_init` / `session_new` / `set_model`) on the kiro path | Two sites. **claude**: `acp/client.py::AcpClient.ensure_ready()` — times cold-start (spawn + session init) and emits in a `finally` so every exit path is measured, with no `phase` attr. **kiro ACP**: `providers/acp.py::_emit_kiro_startup_metric` — one `phase=total` point PLUS one point per internal phase; `spawned` is unconditionally `True` because `_start_kiro_runtime_impl` always spawns a fresh runtime (the warm fast-path returns before reaching either site and is NOT measured). `outcome` defaults to `"error"` so an unexpected exception is never mislabeled `"ready"`. Consumers MUST treat only the end-to-end point (`phase` absent or `total`) as a startup — the phase points are components of one startup. |
| `kirocrew.turn.duration` | histogram (ms) | `outcome` (`ok` / `timeout` / `error`), `session_source` (via `validation.infer_use_case`) | `dashboard/chat_runner.py::_emit_turn_metric`, called at EVENT_COMPLETE after `persist_token_record_async`. `_turn_outcome` maps stop_reason (`""`/`end_turn`/`stop`/`completed` → ok). One histogram powers turn latency p50/p90 AND fault rate. The value is `duration_ms or elapsed_ms`: the acp provider always reports `TurnUsage.duration_ms == 0` (only claude_code fills it), so the caller must pass the locally measured wall clock as `elapsed_ms` or nothing is ever emitted. A still-zero value skips the emit deliberately — absence renders as "no data", whereas a recorded 0 would render as a plausible 0ms p50. **What it measures:** the wall clock starts at turn start, so a turn parked on an interactive tool-approval prompt counts operator thinking time. No finer-grained source exists on the acp path, so this is "turn wall-clock", not pure model latency — a high p90 can mean slow approvals rather than a slow model. |
| `kirocrew.mcp.backend.acquire.duration` | histogram (ms) | `warm` (bool — `not was_spawned`) | `mcp_gateway/gatewayd.py::_emit_backend_acquire_metric` — ensure_backend pre-flight + lazy-spawn paths; acquire-only duration captured before attach_stub/create_task overhead. |
| `kirocrew.mcp.lazy_load.count` / `.duration` | counter + histogram (ms) | `transport` (`stdio`) | `mcp_gateway/gatewayd.py::_emit_lazy_load_metrics` — legacy lazy-spawn path (also emits backend.acquire). |
| `kirocrew.mcp.warm_pool.acquire` | counter | `result` (`hit` / `miss`) | `mcp_gateway/prewarm.py::HotKeyStore.record_outcome` (emitted outside the lock). |
| `kirocrew.skill.lazy_load.count` / `.duration` | counter + histogram (ms) | `hit` (bool) | `skills.py::SkillsLoader.load_skill` via `_emit_lazy_load_metric` (best-effort; never breaks skill loading). |
| `kirocrew.gateway.boot.duration` | histogram (ms) | `server` (`dashboard` / `api`), `outcome` (`ready`) | `dashboard/server.py::start_dashboard` / `start_api_server` — boot-to-ready: wall-clock from the server's `start_time` until full init completes and it is about to accept traffic. Emitted via `metrics/http_metrics.py::record_boot_to_ready`. Best-effort; never blocks startup. |
| `kirocrew.gateway.request.duration` | histogram (ms) | `method` (fixed HTTP-verb allowlist, else `OTHER`), `route_template` (matched aiohttp canonical TEMPLATE, e.g. `/api/artifacts/{slug}`, else `__unknown__`), `status_class` (`1xx`..`5xx` / `other`) | `metrics/http_metrics.py::make_route_latency_middleware` — outermost gateway middleware on BOTH `start_dashboard` and `start_api_server`. Times full in-gateway HTTP handling; upgraded WebSocket connections and `text/event-stream` SSE responses are excluded so connection/turn lifetime cannot pollute request latency. **Bounded cardinality** (see below). |

### Histogram bucket boundaries: per instrument, not shared

Boundaries live in `metrics/provider.py::_HISTOGRAM_BUCKETS_MS`, a metric-name →
boundaries map from which one `View(instrument_name=…)` is built per instrument.
Three families, each sized to its instrument's measured range:

| Family | Range | Instruments |
|---|---|---|
| `_FAST_BUCKETS_MS` | 0.5ms – 60s | `gateway.request`, `mcp.backend.acquire`, `skill.lazy_load` |
| `_STARTUP_BUCKETS_MS` | 1ms – 60s | `session.startup`, `mcp.lazy_load`, `gateway.boot` |
| `_TURN_BUCKETS_MS` | 1s – 1h | `turn.duration` |

**Why not one shared array.** A single 1ms–60s array previously served every
histogram through a catch-all `View(instrument_type=Histogram)`. Its ceiling was
sized for session startup, so the first `kirocrew.turn.duration` sample ever
recorded (227589ms — an agent turn is a whole agent loop including tool
round-trips and any wait on an interactive approval) landed in the `+Inf`
overflow bucket. Since `_pct_from_buckets` can only report an overflow bucket's
LOWER bound, the aggregator returned `p50 == p90 == 60000` — a ceiling artifact
presented as a real latency, while `mean`/`max` (exact, from `sum`/`max`) stayed
correct beside it. `p50 == p90` is the signature of this failure. Instruments in
this system span six orders of magnitude (sub-ms pooled acquires to multi-minute
agent turns), so one array must sacrifice either fast-end resolution or slow-end
truth.

**Why there is no catch-all fallback.** The OTEL SDK applies EVERY matching
View, not the first. A per-instrument View plus a catch-all therefore publishes
the same metric name twice with different bounds. The SDK offers no negation in
View matching, so the catch-all had to be removed rather than narrowed.

**Boundary generations never merge.** Bounds are baked into each data point at
record time, so any boundary change makes the 14-day scan window straddle two
incompatible generations of one metric. `handlers/telemetry.py::_Hist` therefore
groups data points by their EXACT `explicit_bounds` and reports statistics from a
single group — **the one holding the newest data point**. Selection is by recency,
not volume: majority selection would let a stale generation keep winning while it
out-counted the new one, so right after a boundary change the old bounds would be
reported for up to the whole 14-day window — for `turn.duration` that means
continuing to serve the ceiling-pinned percentiles this grouping exists to remove,
while omitting the new samples. Recency makes the change take effect on the first
post-change sample; the reported population is then small but truthful, and
`count` says so. (`count` remains a tie-break for data points carrying no
`time_unix_nano`.) **Outcome tallies
are grouped too** — accumulated inside `_Hist` rather than alongside it, because
scoping only the buckets and count would leave the outcome breakdown summing
across generations: the page would show N turns beside an outcome bar totalling
more than N, and a `fault_rate` computed over a different population than the
latency next to it. `other_generations` (0 = a clean window; >0 = the window
straddles a boundary change and only the dominant generation is reported) and
`total_count` (samples across EVERY generation) are therefore returned by
`_Hist.stats()` itself, so they travel with every set of numbers they qualify —
the `startup` blocks, the `turn` block, each `other` histogram, and each
per-attribute split.

The dashboard renders the PAIR, not the generation count: it shows
"showing 1,134 of 2,926 samples" beside the affected figure. A generation count
is an internal unit a reader cannot convert into missing data, so "1 older
generation" left a truncated `n=1134` unreconcilable against the `2837 hit`
counter next to it, while the shown/total pair is directly comparable to both.
`other_generations` remains the structural fact (how many incompatible groups the
window holds) and stays in the response for diagnostics.

They are deliberately NOT pasted on by the response builder per block. That is
how it shipped, and the generic `other` instruments were never given the field:
the MCP acquire card reported one generation's `n` (1,154 of 2,926 real samples)
beside a full-window counter, with nothing anywhere saying a generation had been
dropped. A statistic and the caveat that makes it readable are one value, not
two.

This is load-bearing, not defensive: the historical shared array and
`_TURN_BUCKETS_MS` have the SAME bucket-count length, so a length-only check
would have merged them positionally — adding a pre-change sample from the old
`+Inf` bucket into the new `+Inf` bucket and reporting **p90 = 3,600,000ms (one
hour)**, while a 5s sample landed in a 5-minute bucket. Grouping also keeps
`count`/`sum`/`min`/`max` consistent with the percentiles; accumulating those
across generations while only one generation's buckets survived would describe a
mean over one population and percentiles over another.

**Completeness is therefore load-bearing.** With no catch-all, a histogram
missing from the map silently falls back to OTEL's default 10s-ceiling
boundaries — reintroducing the same class of bug. `test/metrics/
test_provider_bucket_views.py` scans the source for `kirocrew.*.duration` metric
names and fails when one has no map entry (and when a map entry has no emitting
call site). It also pins the no-duplicate-streams property and asserts the
227589ms regression sample no longer overflows. **When adding a duration
histogram, add it to `_HISTOGRAM_BUCKETS_MS`.**

### Bounded cardinality of `kirocrew.gateway.request.duration` (rec #1)

The per-route latency label `route_template` is **never** the concrete request
path, query, id, or body — it is the aiohttp route TEMPLATE
(`/api/items/{item_id}`), whose `{…}` placeholders are constants baked into the
route table. The bounding is structural: `collect_route_templates(app)` snapshots
the finite set of registered templates once (lazily, on first request, after all
routes — including edition-contributed and post-middleware routes — are present),
and `route_template()` returns a value ONLY if it is a member of that frozen set;
anything else (an unmatched 404 aiohttp `SystemRoute`, or a template not in the
snapshot) collapses to the single sentinel `__unknown__`. Therefore the distinct
`route_template` label values are bounded by `len(known_templates) + 1`, a
constant fixed at startup that cannot grow with traffic. Combined with the fixed
`method` allowlist (≤ 8 values) and the fixed `status_class` domain (6 values),
total series are bounded by `(len(known_templates) + 1) × 8 × 6`. The test
`test/metrics/test_gateway_http_metrics.py::test_bounded_cardinality_under_many_distinct_ids`
proves this against real OTEL data points: 100 distinct ids yield exactly ONE
`route_template` value. **Privacy:** the only request-derived labels are
`method` / `route_template` / `status_class` — no prompt, content, token, path,
query, user id, or secret is ever recorded, and every string label still passes
the recorder's `redact()` guardrail.

Note: the fork's primary kiro chat path uses `AcpSessionProvider.ensure_ready()`
(a no-op liveness check), so this histogram measures AcpClient-based cold starts
(knowledge `llm_pool`, review pools, client-internal callers).

## Dashboard handler

`dashboard/handlers/telemetry.py` — `GET /api/telemetry/startup` scans the JSONL
shards (14-day window, shard-fingerprint + 30s-TTL cache, aggregation offloaded
via `asyncio.to_thread`), aggregates the startup histogram into p50/p90 split by
cold/warm (`spawned` attr) + outcome + daily series, the turn histogram into a
`turn` block (stats + outcome counts + `fault_rate`), and generically surfaces
every other `kirocrew.*` metric (`other` list) so new emit call-sites appear
without a handler change. Percentiles are interpolated from bucket counts (made
meaningful by the DELTA temporality + explicit-bucket View). Security: the
user-configurable `telemetry.local_dir` and each shard pass `validate_file_path`
(sensitive-path check) before any read. Cross-process: metrics are emitted by
the ACP/gateway processes, so reading the durable shards is the only correct
path (an in-memory reservoir in the dashboard process would never see them).

The production dashboard does not request or render this compatibility
endpoint: `website/src/pages/TelemetryPanel.tsx` is a static disabled notice
with no query or polling. The handler remains available for audit and tests
that inspect manually supplied legacy shards.

**`other` histogram splits (`_OTHER_SPLIT_ATTRS`).** An `other` histogram also
carries a `splits` map (`"attr=value"` -> the same stats shape) for a NAMED set
of low-cardinality attributes — currently `warm` only. This exists so one side of
a split can be reported alone: the dashboard's cold-spawn figure is
`acquire.splits["warm=false"]`. Splitting on every attribute present was
rejected because `gateway.request.duration` carries method+route, which would
grow one sub-histogram per endpoint and force an arbitrary truncation cap on the
payload; a named boolean keeps the split two entries wide with no cap.

Note that `kirocrew.mcp.lazy_load.*` is NOT the cold-spawn signal even though its
name suggests it. It is emitted only from the legacy pre-`ensure_backend` spawn
path, which modern stubs never take, so it records nothing on a current
deployment (0 data points across 47 shards / 12 days observed) while real cold
spawns are recorded on the acquire histogram under `warm=false`. The instrument
stays because that legacy path can still execute for an old stub; the dashboard
does not read it.

**Startup phase gating.** Only the end-to-end startup point (`phase` absent, as
on the claude path, or `phase=total` from the kiro path) feeds the startup
totals — count, cold/warm split, outcome, daily series, and the bucket
distribution. Per-phase points are aggregated separately into
`startup.phases[]` (`{name, count, p50_ms, p90_ms, …}`). Counting them as
startups multiplies the startup count by the number of phases and sums several
unrelated latency distributions into one set of buckets, which renders as a
spurious multi-modal "distribution".

**`context` block (compatibility response only).** The response may carry
per-turn context-window occupancy — `{turns, p50_pct, p90_pct, max_pct,
sessions[]}` — sourced from the
legacy token-row reader below, NOT from the OTEL shards: occupancy is a
per-session ratio and slot keys are unbounded-cardinality, which must not become
a metric label. `sessions[]` is the top 8 by peak occupancy, each reporting peak
plus the LATEST turn's identity (agent/model/surface) and absolute
used/window. Rows whose window is missing or zero are skipped rather than
defaulted. The block is `null` when no row carries the fields. The source-only
runtime does not append new token rows; manually supplied legacy shards remain
readable for compatibility.

## Legacy per-turn token usage rows (compatibility only)

Separate from the OTEL histogram sink above (`~/.kiro/crew/metrics/`, DELTA
histograms for trends/alerting), the dashboard retains a **legacy row reader**
for audit/test compatibility. It parses one JSON object per historical
model-spending turn from `<data home>/usage/tokens/YYYY-MM-DD.jsonl` (shards
partitioned by the user's local date). The source-only runtime does not append
new rows, and legacy persistence flags do not change that. The compatibility
builders `dashboard/handlers/usage.py::persist_token_record` (sync) /
`persist_token_record_async` still produce an in-memory row for callers and
tests, then drop it before filesystem I/O. Aggregation uses
`_parse_token_history` (30-day window, shard-fingerprint + 120s-TTL cache).

Each row (`_build_token_record`) carries:

| field | type | meaning |
|-------|------|---------|
| `_type` | str | always `"tokens"` (record discriminator) |
| `ts` | str | ISO-8601 local timestamp of the turn |
| `slot` | str | chat slot / session key |
| `provider` | str | LLM backend (`acp` / `claude_code` / `bedrock` / …), `""` if unknown |
| `model` | str | model id for the turn |
| `input` / `output` | int | prompt / completion tokens (structurally `0` on the ACP backend — kiro-cli bills credits only) |
| `cache_create` / `cache_read` | int | cache-write / cache-read tokens |
| `cost` | float | provider-reported USD cost (`0.0` on ACP) |
| `credits` | float | kiro-cli per-turn credit spend (float-coerced) |
| `turns` | int | provider `num_turns` |
| `duration_ms` | int | provider-reported turn duration (`0` on ACP) |
| `surface` | str | **(#647)** dispatch origin — `dashboard`, `cron`, `subagent`, `monitor`, `heartbeat`, `webhook`, `task_runner`, `workflow`; `""` if unset |
| `agent` | str | **(#647)** agent id resolved for the turn; `""` if unset |
| `context_used` | int | **(#647)** context-window tokens occupied after the turn (int-coerced) |
| `context_window` | int | **(#647)** served context-window size in tokens (int-coerced) |

The last four fields are **additive** — every field defaults (`""` / `0`) so
existing callers stay valid and pre-#647 shards (which lack the keys) remain
parseable; readers must tolerate their absence. `context_used` / `context_window`
are read from the provider at the persist call site via
`usage.read_context_tokens(source)`, which calls the provider's public
`context_used_tokens()` / `context_window_tokens()` accessors
(`providers/base.py`, implemented for ACP in `providers/acp.py` +
`acp/session_provider.py`) behind `getattr` guards and returns `(0, 0)` on any
missing accessor or exception — so non-ACP providers and test doubles record
zeros and the analytics helper never breaks the turn it measures. `surface`
lets background turn-dispatch surfaces (cron/subagent/monitor/heartbeat/webhook/
task_runner/workflow) attribute their spend; zero-token surfaces (cron
`script=`/`command=` modes, heartbeat maintenance ticks) never call a model and
must not write a row.

**Read side (not a production UI surface).** `usage.context_occupancy(days)`
aggregates these rows into
per-turn occupancy percentiles plus a per-session peak ranking (own
shard-fingerprint + 30s-TTL cache, same contract as `_parse_token_history`), and
`handlers/telemetry.py` serves it as the `context` block of
`GET /api/telemetry/startup` for compatibility (a plain module-scope import —
`handlers.usage` imports nothing from `dashboard.handlers`, so there is no
cycle to dodge). The production TelemetryPanel never requests this data.
Without it the two fields were
write-only: recorded on every turn since #647, read by nothing.

Tests: `test/test_usage.py` (`TestReadContextTokens`,
`TestBuildTokenRecordContextFields`, `TestPersistTokenRecord*`),
`test/metrics/test_context_occupancy.py` (aggregation, skips, latest-turn wins).

## Circular-import rule

`metrics/provider.py` imports `config.loader` at module top; call sites reached
from inside `config.loader`'s import chain (e.g. `acp/client.py`) MUST import
`get_recorder` lazily (inside the function) so the provider is never loaded
during that chain.

## Outbound telemetry boundary (beacon and install receipts)

The VibecodersCrew source-only distribution has one production telemetry rule:
**nothing leaves the host**. The runtime constants
`PRODUCT_TELEMETRY_ENABLED = false` (OTEL/local metrics) and
`OUTBOUND_TELEMETRY_ENABLED = false` (the beacon and app-install receipt)
are hard-disabled edition boundaries. Config values, environment variables,
dashboard controls, CLI commands, and endpoint arguments cannot override them.

| Path | Purpose | Runtime behavior |
|------|---------|------------------|
| `metrics/` | Local operational metrics | `get_recorder()` is a no-op; no JSONL writer or OTLP exporter is constructed |
| `beacon.py` | Legacy anonymous heartbeat | `send()` returns `False` before reading state or opening a URL |
| `apps/install_receipt.py` | Legacy official-app receipt | The sender is suppressed by the same outbound boundary |
| `usage/tokens/` | Historical cost/context rows | The source-only runtime reads legacy rows for compatibility; it does not append new rows |

`beacon.status()` is deliberately truthful about the boundary: it reports
`enabled: false`, `would_send: false`, no configured endpoint, and the reason
`disabled in VibecodersCrew`. The Privacy endpoint and CLI status command may
still be used as diagnostics; reading status never materializes an install id.

The inherited beacon/receipt implementation remains in the tree so upstream
compatibility and audit tests can inspect its payload and suppression logic.
Those tests may temporarily monkeypatch `OUTBOUND_TELEMETRY_ENABLED` in an
isolated process. Such a test seam is not a supported runtime configuration and
must never be used by gateway startup, dashboard handlers, app listing, or
install paths.

### Egress and user actions

No startup path performs an outbound `urllib` request, creates beacon state, or
schedules a beacon worker. No successful app
install/update emits a receipt. Setting
`telemetry.beacon_enabled`, `telemetry.beacon_endpoint`,
`KIROCREW_TELEMETRY_DISABLED`, or `otlp_endpoint` cannot enable egress;
the first hard-disabled gate wins. The documented setup and update commands
therefore remain offline with respect to telemetry.

### Compatibility data

Historical local metric shards and token rows are never uploaded by this
edition. Existing files may be inspected by the dashboard's compatibility
readers, but no new telemetry files are created and no retention/pruning job is
started. Operators who need to remove old files can do so with their normal
local data-management tools; KiroCrew does not transmit them.

### Specification/test contract

The production boundary is pinned by:

- `src/kiro_crew/metrics/provider.py` and
  `src/kiro_crew/beacon.py` hard-disabled constants;
- `test/metrics/test_provider.py`, which asserts the no-op recorder and no
  exporter construction;
- `test/test_beacon_status_endpoint.py`, which asserts status remains off even
  when config stores `beacon_enabled: true`;
- `test/test_install_receipt.py`, whose network tests explicitly replace the
  constant and therefore do not grant runtime permission.

When a future edition wants outbound telemetry, it must change this
specification, the distribution boundary, the privacy disclosure, and the
tests together. A config-only switch is insufficient.
