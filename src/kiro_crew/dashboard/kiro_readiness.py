# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Shared pre-enqueue guard for Kiro-backed dashboard sessions.

Readiness is probed once at gateway start and then only on an explicit user
action (see ``kiro_prerequisite.KiroPrerequisiteService.session_ready``), so the
latched value can be arbitrarily stale. That splits the callers in two:

* **Ordinary sends are UNGATED.** A stale not-ready value must never block a
  send: the real ACP attempt is the authority, and it reports a signed-out CLI as
  an actionable ``AcpAuthRequired`` error in the chat transcript. Blocking on
  latched state was the stuck case — a user who signed in from a terminal stayed
  locked out until something re-probed. These handlers mutate nothing before the
  turn, so a failed turn costs only an error card.
* **Endpoints that act BEFORE the turn still BLOCK**
  (:func:`reject_if_kiro_unverified`) — the poll-driven ``kiro-cli`` spawn sites
  and the destructive reruns. Neither can rely on the ACP attempt as its
  authority: one has no turn at all, the other has already rewritten durable
  history by the time the turn fails. See
  ``docs/system-specs/modules/acp-client.md`` § "Poll-driven spawn sites are
  readiness-gated".
"""

from __future__ import annotations

import asyncio
import time

from aiohttp import web

from kiro_crew.config.loader import SUPPORTED_PROVIDER_IDS
from kiro_crew.kiro_prerequisite import KiroPrerequisiteService
from kiro_crew.providers.codex import CodexReadiness, probe_codex_readiness

_KIRO_NOT_READY_RESPONSE = {
    "error": "Kiro CLI setup or sign-in is required before starting a session.",
    "code": "kiro_prerequisite_required",
}
_CODEX_READINESS_CACHE_KEY = "codex_readiness_cache"
_CODEX_READINESS_PROBE_LOCK_KEY = "codex_readiness_probe_lock"

# How stale a probe may be and still authorize a destructive or spawning call.
# Small enough that an external logout cannot linger behind this gate, large
# enough that a burst of callers collapses onto one probe.
_VERIFY_MAX_AGE_SECS = 30.0


async def kiro_session_ready(service: object) -> bool:
    """Return the service's latched readiness. Fails closed on a bad service."""

    if not isinstance(service, KiroPrerequisiteService):
        return False
    return await service.session_ready()


async def kiro_verified_ready(service: object) -> bool:
    """Return readiness backed by a probe that is FRESH ENOUGH to authorize on.

    The latch alone cannot authorize these callers. It is written at boot and
    narrowed only when a chat turn observes ``AcpAuthRequired``, so an external
    logout with no chat turn in between leaves it ``ready=True`` indefinitely —
    and every one of this gate's callers acts irreversibly on that answer
    (deletes history, or spawns a browser-opening ``kiro-cli``). "Probe at boot
    only" is the right rule for the send path, which risks nothing; it is the
    wrong rule for authorization.

    So this re-probes when the latch is older than
    ``_VERIFY_MAX_AGE_SECS``. That is bounded work — it happens only on a
    destructive rerun or a poll tick, never on the message hot path — and the
    service's own short cache collapses bursts (e.g. the three destructive
    routes, or several pollers firing together) into one probe.
    """

    if not isinstance(service, KiroPrerequisiteService):
        return False
    return await service.verified_ready(max_age_secs=_VERIFY_MAX_AGE_SECS)


async def codex_readiness(
    request: web.Request,
    *,
    max_age_secs: float | None = None,
    allow_probe: bool = True,
) -> CodexReadiness:
    """Return cached Codex auth state, probing only when explicitly allowed.

    ``probe_codex_readiness`` runs the local, read-only ``codex login status``
    command. During an explicit browser login operation callers set
    ``allow_probe=False`` so operation-status polls never spawn Codex. The
    first read after the operation finishes invalidates the cache and performs
    exactly one fresh local check; the result is then cached for subsequent
    reads.
    """

    cached = request.app.get(_CODEX_READINESS_CACHE_KEY)
    now = time.monotonic()

    def _fresh_cached(
        value: object,
        *,
        age_limit: float | None,
        checked_at_now: float,
    ) -> CodexReadiness | None:
        if not (isinstance(value, tuple) and len(value) == 2):
            return None
        checked_at, readiness = value
        if not isinstance(checked_at, (int, float)) or not isinstance(readiness, CodexReadiness):
            return None
        if age_limit is None or checked_at_now - checked_at <= age_limit:
            return readiness
        return None

    readiness = _fresh_cached(cached, age_limit=max_age_secs, checked_at_now=now)
    if readiness is not None:
        return readiness
    if not allow_probe:
        # A running login operation owns the readiness state. Returning the
        # previous cache (even if stale) keeps operation polls subprocess-free;
        # with no cold cache, expose a neutral not-ready result until the one
        # post-operation check runs.
        if isinstance(cached, tuple) and len(cached) == 2:
            cached_readiness = cached[1]
            if isinstance(cached_readiness, CodexReadiness):
                return cached_readiness
        return CodexReadiness(False, False, "Codex sign-in is still running.")

    # Multiple owners/non-owner dashboard tabs can observe completion together.
    # Serialize the local probe and re-check the cache after waiting so the
    # transition performs one status command rather than one per request.
    lock = request.app.get(_CODEX_READINESS_PROBE_LOCK_KEY)
    if not isinstance(lock, asyncio.Lock):
        lock = asyncio.Lock()
        request.app[_CODEX_READINESS_PROBE_LOCK_KEY] = lock
    async with lock:
        now = time.monotonic()
        cached = request.app.get(_CODEX_READINESS_CACHE_KEY)
        readiness = _fresh_cached(cached, age_limit=max_age_secs, checked_at_now=now)
        if readiness is not None:
            return readiness
        readiness = await probe_codex_readiness()
        request.app[_CODEX_READINESS_CACHE_KEY] = (now, readiness)
        return readiness


def _service(request: web.Request) -> object:
    service = request.app.get("kiro_prerequisite_service")
    if service is None:
        service = getattr(request.app.get("state"), "kiro_prerequisite_service", None)
    return service


async def reject_if_kiro_unverified(request: web.Request) -> web.Response | None:
    """Return 503 for the endpoints that must fail closed on a stale latch.

    Two classes qualify, both because the ACP attempt cannot be their authority:

    * **Poll-driven ``kiro-cli`` spawn sites** (``/api/models``,
      ``/api/sessions/usage``) — they shell out on a timer with no turn to report
      into, and an unauthenticated spawn opens an interactive browser login (and
      ``kiro-cli chat`` hangs) on every poll interval.
    * **Destructive reruns** (regenerate, edit-resend, rewind) — they truncate
      and PERSIST session history *before* the background turn starts, so a
      signed-out install would drop prior turns while returning 200. There is no
      later error card that can undo a durable rewrite, so the check has to
      happen before the mutation.
    * **``POST /v1/chat/completions``** — no transcript the caller reads. Its
      collectors take only ``chunk``/``assistant`` roles, so an ``AcpAuthRequired``
      turn's ``error`` card is invisible and the request would answer 200 with
      empty content, which an SDK client cannot tell apart from a model that said
      nothing.

    Ordinary sends are deliberately NOT gated: they mutate nothing up front, so a
    stale latch must not block them (see the module docstring). A missing or
    invalid service fails closed here.

    These callers must not trust the latch in EITHER direction, so this uses
    :func:`kiro_verified_ready` — a stale ``ready=True`` is as dangerous as a
    stale ``ready=False`` here (it authorizes the history rewrite or the
    browser-opening spawn), and only these paths pay for the re-probe.
    """

    state = request.app.get("state")
    sessions = getattr(state, "sessions", None)
    # Missing session wiring is a server misconfiguration. Keep the guard
    # fail-closed instead of treating an unwired request as a Codex profile.
    if sessions is None:
        if await kiro_verified_ready(_service(request)):
            return None
        # Keep this body explicit so the static error-code contract can see the
        # machine-readable identifier even though the shared constant is used
        # by the provider-specific branch below.
        return web.json_response(
            {
                "error": "Kiro CLI setup or sign-in is required before starting a session.",
                "code": "kiro_prerequisite_required",
            },
            status=503,
        )
    configured_provider = getattr(sessions, "configured_provider", "codex")
    if configured_provider not in SUPPORTED_PROVIDER_IDS:
        return web.json_response(
            {
                "error": "Unsupported provider configuration; choose Codex or ACP.",
                "code": "unsupported_provider",
            },
            status=503,
        )
    if isinstance(configured_provider, str) and configured_provider == "codex":
        readiness = await codex_readiness(request, max_age_secs=_VERIFY_MAX_AGE_SECS)
        if readiness.ready:
            return None
        return web.json_response(
            {
                "error": "Codex CLI setup or ChatGPT sign-in is required before starting a session.",
                "code": "codex_prerequisite_required",
            },
            status=503,
        )
    if await kiro_verified_ready(_service(request)):
        return None
    return web.json_response(_KIRO_NOT_READY_RESPONSE, status=503)
