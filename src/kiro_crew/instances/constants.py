# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Tunable constants for the Instances feature.

Isolated in this module so resource limits and defaults can be adjusted in one
place without hunting through the registry / tunnel-manager code.

These values are the *defaults* for the corresponding ``InstancesConfig`` fields
in ``kiro_crew.config.loader``; a user can override them via
``kirocrew config set instances.<key> <value>``. Keeping the canonical default
here (and referencing it from the dataclass) means the constant and the config
default can never drift apart.
"""

from __future__ import annotations

# Maximum number of remote instances kept "warm" (iframe mounted + tunnel +
# WebSocket live) at once. Each warm instance is a full dashboard SPA, so this
# bounds memory/socket usage; least-recently-used iframes beyond the cap are
# evicted from the local viewport. The tunnel remains under explicit owner
# control and is never reopened by the eviction path.
DEFAULT_WARM_SET_CAP: int = 5

# First local loopback port handed out for an SSH ``-L`` forward. The port
# allocator increments from here, skipping ports already in use. Chosen to sit
# just above the default dashboard port (7777).
DEFAULT_TUNNEL_BASE_PORT: int = 7778

# Enable SSH transport compression (``ssh -C``) on instance tunnels. The whole
# remote dashboard travels over this single forwarded stream: the SPA bundle on
# first connect plus every subsequent API/WebSocket frame. That payload is
# JS/HTML/JSON — highly compressible (typically 3-5x), and the gateway does not
# gzip its HTTP responses, so nothing is double-compressed. Default on because
# the dominant deployment is a dedicated remote gateway host where spare CPU to
# save bandwidth on a high-latency/low-throughput link is the right trade. On a
# fast/local link compression can be marginally slower, so it stays tunable via
# ``kirocrew config set instances.ssh_compression false``. See §5.2.
DEFAULT_SSH_COMPRESSION: bool = True

# Health-probe cadence/threshold for a connected tunnel. Poll every interval,
# and after this many *consecutive* failures treat the tunnel as unhealthy
# and leave it disconnected until an explicit Connect/Retry action. interval <=
# 0 disables the probe.
DEFAULT_PROBE_INTERVAL_SECS: int = 30
DEFAULT_PROBE_FAILURE_THRESHOLD: int = 3

# Compatibility limit for the private explicit recovery seam. Normal tunnel
# drops schedule no recovery; the owner must Connect/Retry. Reset to 0 once a
# manually invoked rebuild succeeds.
DEFAULT_MAX_RECOVERY_ATTEMPTS: int = 8

# Upper bound on the compatibility setting instances.max_recovery_attempts. A
# value above this is clamped down to it (with a warning) for callers that still
# invoke the private explicit recovery seam.
MAX_RECOVERY_ATTEMPTS_CEILING: int = 100

# Compatibility cap (secs) on the per-attempt backoff for manually invoked
# recovery. No background task consumes this value.
DEFAULT_RECOVER_BACKOFF_MAX_SECS: float = 30.0

# Upper bound (secs) on a user-configured instances.recover_backoff_max_secs. A
# larger value is clamped down to it (with a warning) for compatibility with
# the explicit recovery seam.
RECOVER_BACKOFF_MAX_CEILING_SECS: float = 300.0

# Legacy compatibility value for clients that display token TTL metadata. Token
# minting is explicit; no timer uses this fraction.
DEFAULT_TOKEN_REFRESH_FRACTION: float = 0.8

# Timeout (secs) for the loopback liveness probe that validates a *stored* token
# before the API hands it to the browser on (re)connect. A stored token can go
# stale while the tunnel stays CONNECTED (for example, a remote `kirocrew restart`
# that invalidates tokens); an iframe loaded with a stale
# token gets a server-rendered 403 page, so the SPA never boots to fire the
# `mc-auth-expired` notification. The probe (GET /api/status?token=... over
# the existing tunnel — no SSH) closes that initial-load gap. It is
# deny-by-default: anything but a positive 2xx (including a timeout/connection
# error) is treated as invalid and forces a fresh mint; if that mint also fails
# the link is genuinely down and the caller returns an error rather than serving
# an unconfirmed token. Kept tight so a tab activation never blocks perceptibly.
DEFAULT_TOKEN_PROBE_TIMEOUT_SECS: float = 2.0
