# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Authenticated dashboard handlers for Kiro CLI first-run setup."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Any

from aiohttp import web

from kiro_crew.config.loader import SUPPORTED_PROVIDER_IDS
from kiro_crew.dashboard.kiro_readiness import codex_readiness
from kiro_crew.kiro_prerequisite import (
    OFFICIAL_INSTALL_DOCS_URL,
    KiroPrerequisiteService,
    OperationStatus,
    PrerequisiteBusyError,
    PrerequisiteStatus,
)
from kiro_crew.providers.codex import (
    CodexLoginBusyError,
    CodexLoginService,
    CodexReadiness,
)
from kiro_crew.sel import sel

logger = logging.getLogger(__name__)
_LOCAL_DASHBOARD_OWNER_SUBJECTS = frozenset({"local-app", "local-startup"})


def _not_ready_snapshot(initial_setup_complete: bool = False) -> dict[str, Any]:
    """A retryable not-ready snapshot for when a status probe cannot run.

    Shaped exactly like ``KiroPrerequisiteService.snapshot()`` (built from the
    same dataclasses so it cannot drift), it reports the CLI as installed but
    not signed in so the dashboard shows a retry path rather than a 500 flash.

    ``initial_setup_complete`` is carried through from the service so a failed
    probe does not demote a returning user to first-run — reporting ``False``
    here makes the SPA restore the full-screen first-run setup gate for someone
    who finished setup long ago.
    """

    result: dict[str, Any] = asdict(
        PrerequisiteStatus(
            platform="gateway",
            installed=True,
            initial_setup_complete=initial_setup_complete,
        )
    )
    result["operation"] = asdict(
        OperationStatus(
            status="failed",
            message="Could not check Kiro CLI. Retry the gateway check.",
            error="Kiro CLI status check could not run.",
        )
    )
    return result


def _service(request: web.Request) -> KiroPrerequisiteService:
    service = request.app.get("kiro_prerequisite_service")
    if not isinstance(service, KiroPrerequisiteService):
        raise web.HTTPServiceUnavailable(
            text="Kiro prerequisite service unavailable.",
            content_type="text/plain",
        )
    return service


def _codex_login_service(request: web.Request) -> CodexLoginService:
    """Return the per-gateway Codex login coordinator.

    Construction is local-only and side-effect free. The subprocess is created
    by :meth:`CodexLoginService.start` only from the explicit POST handler.
    ``on_finished`` invalidates the readiness cache so the next status poll
    observes the credential store written by Codex itself.
    """

    service = request.app.get("codex_login_service")
    if isinstance(service, CodexLoginService):
        return service

    def _invalidate_readiness() -> None:
        request.app["codex_readiness_cache"] = None

    service = CodexLoginService(on_finished=_invalidate_readiness)
    request.app["codex_login_service"] = service
    return service


def _codex_operation_payload(service: CodexLoginService) -> dict[str, Any]:
    operation = service.snapshot()
    return {
        "kind": "login" if operation.status != "idle" else "",
        "status": operation.status,
        "message": operation.message,
        "detail": operation.detail,
        "url": "",
        "error": operation.error,
        "code": operation.code,
    }


def _codex_snapshot(
    readiness: CodexReadiness,
    *,
    operation: dict[str, Any],
) -> dict[str, Any]:
    """Shape Codex readiness like the existing prerequisite status contract."""

    snapshot = asdict(
        PrerequisiteStatus(
            platform="Codex App Server",
            installed=readiness.installed,
            authenticated=readiness.authenticated,
            ready=readiness.ready,
            initial_setup_complete=readiness.ready,
            docs_url="https://developers.openai.com/codex/cli/",
        )
    )
    snapshot["provider"] = "codex"
    snapshot["can_auto_install"] = False
    snapshot["can_login"] = readiness.installed
    # Codex login is a provider action owned by the local dashboard; the
    # legacy Kiro installer/login permissions do not apply to this payload.
    snapshot["setup_allowed"] = False
    snapshot["operation"] = operation
    if readiness.ready:
        snapshot["operation"] = {
            "kind": "",
            "status": "idle",
            "message": "Codex is ready.",
            "detail": "",
            "url": "",
            "error": "",
            "code": "",
        }
    elif not operation.get("message"):
        snapshot["operation"] = {
            **operation,
            "status": "failed",
            "message": "Install Codex, then click Sign in to Codex to open the browser login.",
            "error": readiness.detail,
        }
    return snapshot


def _unsupported_provider_snapshot(provider: object) -> dict[str, Any]:
    """Return a fail-closed status without selecting either backend."""

    configured = str(provider or "unknown")
    return {
        "platform": "gateway",
        "provider": configured,
        "installed": False,
        "authenticated": False,
        "ready": False,
        "initial_setup_complete": False,
        "can_auto_install": False,
        "can_login": False,
        "repair_required": False,
        "docs_url": "",
        "setup_allowed": False,
        "operation": {
            "kind": "",
            "status": "failed",
            "message": "Unsupported provider configuration.",
            "detail": "",
            "url": "",
            "error": "Select either Codex or ACP in agent.provider.",
            "code": "unsupported_provider",
        },
    }


def _redacted_codex_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Keep the readiness bit while hiding host/provider operation details."""

    operation = snapshot.get("operation") if isinstance(snapshot, dict) else {}
    operation = operation if isinstance(operation, dict) else {}
    return {
        "platform": "gateway",
        "installed": False,
        "authenticated": False,
        "ready": bool(snapshot.get("ready")),
        "initial_setup_complete": bool(snapshot.get("initial_setup_complete")),
        "can_auto_install": False,
        "can_login": False,
        "repair_required": False,
        "docs_url": OFFICIAL_INSTALL_DOCS_URL,
        "setup_allowed": False,
        "sandbox_unavailable": False,
        "sandbox_failure_kind": "",
        "sandbox_detail": "",
        "missing_agent_specs": [],
        "agent_spec_repair_error": "",
        "operation": {
            "kind": "",
            "status": str(operation.get("status") or "idle"),
            "message": str(operation.get("message") or ""),
            "detail": "",
            "url": "",
            "error": "",
            "code": "",
        },
    }


def _caller(request: web.Request) -> str:
    user = request.get("user", "")
    return str(user) if user else "dashboard-user"


def _is_dashboard_owner(request: web.Request) -> bool:
    """Return whether a signed dashboard identity may operate host setup."""

    state = request.app["state"]
    owner_id = str(getattr(state, "owner_id", "") or "")
    caller = str(request.get("user") or "")
    return request.get("app") == "" and (
        (owner_id and caller == owner_id)
        or (not owner_id and caller in _LOCAL_DASHBOARD_OWNER_SUBJECTS)
    )


async def _dashboard_owner_only(request: web.Request) -> web.Response | None:
    """Require the configured owner or a signed standalone-local identity."""

    if _is_dashboard_owner(request):
        return None

    caller = str(request.get("user") or "")
    audit_caller = str(request.get("app") or caller or "unknown")

    def _audit() -> None:
        sel().log_api_access(
            caller=audit_caller,
            operation="kiro_prerequisite_access",
            outcome="denied",
            source="dashboard",
            resources=request.path,
            error="dashboard owner required",
        )

    try:
        await asyncio.to_thread(_audit)
    except Exception:
        logger.debug("Could not audit denied Kiro prerequisite access", exc_info=True)
    return web.json_response(
        {"error": "dashboard owner required", "code": "dashboard_owner_required"},
        status=403,
    )


async def api_kiro_prerequisite_status(request: web.Request) -> web.Response:
    """GET /api/kiro-prerequisite — current install/login readiness.

    Reads LATCHED state by default: readiness is probed only on explicit
    request, so the SPA's background poll costs no ``kiro-cli`` subprocess.
    ``?refresh=1`` (the gate's Refresh / Check again button) is the explicit
    user action that forces a real probe.
    """

    if request.get("app") != "":
        denied = await _dashboard_owner_only(request)
        assert denied is not None
        return denied

    state = request.app.get("state")
    sessions = getattr(state, "sessions", None)
    configured_provider = getattr(sessions, "configured_provider", "codex")
    if configured_provider not in SUPPORTED_PROVIDER_IDS:
        snapshot = _unsupported_provider_snapshot(configured_provider)
        if _is_dashboard_owner(request):
            return web.json_response(snapshot)
        return web.json_response(_redacted_codex_snapshot(snapshot))
    if isinstance(configured_provider, str) and configured_provider == "codex":
        login_service = request.app.get("codex_login_service")
        operation = (
            _codex_operation_payload(login_service)
            if isinstance(login_service, CodexLoginService)
            else {
                "kind": "",
                "status": "idle",
                "message": "",
                "detail": "",
                "url": "",
                "error": "",
                "code": "",
            }
        )
        force = request.query.get("refresh") in ("1", "true") and _is_dashboard_owner(request)
        # While the explicit browser login owns the operation, every status
        # read is an in-memory snapshot. The first read after it finishes sees
        # the cache invalidation from ``CodexLoginService._notify_finished``
        # and performs the one local ``codex login status`` check.
        readiness = await codex_readiness(
            request,
            max_age_secs=0.0 if force else None,
            allow_probe=operation.get("status") != "running",
        )
        snapshot = _codex_snapshot(readiness, operation=operation)
        return web.json_response(
            snapshot if _is_dashboard_owner(request) else _redacted_codex_snapshot(snapshot)
        )

    # Only an owner may force a host probe; a non-owner's refresh reads latched
    # state like any other poll (they receive the redacted payload regardless).
    force = request.query.get("refresh") in ("1", "true") and _is_dashboard_owner(request)

    # Resolve the service OUTSIDE the guard: a genuinely unwired service is a
    # real misconfiguration that must stay a 503, not be masked as a 200
    # not-ready. Only the probe itself is guarded.
    service = _service(request)
    try:
        snapshot = await service.snapshot(force=force)
    except asyncio.CancelledError:
        raise
    except web.HTTPException:
        raise
    except Exception:
        # A transient probe failure must not surface as a 500 that flashes the
        # full-screen "could not check Kiro CLI" gate. Report a retryable
        # not-ready snapshot so the dashboard keeps polling. (The probe layer
        # already degrades most failures; this is the last-resort backstop.)
        # The first-run bit is read from the data home, not the probe, so it
        # survives this path and keeps a returning user out of first-run setup.
        logger.warning("Kiro prerequisite status probe failed", exc_info=True)
        snapshot = _not_ready_snapshot(bool(service.initial_setup_complete))
    if _is_dashboard_owner(request):
        return web.json_response({**snapshot, "setup_allowed": True})

    # Authorized non-owner dashboard users need the readiness bit so the
    # application gate does not lock them out after the owner completes setup.
    # Do not expose the host platform, candidate state, operation output, URLs,
    # or mutations to those users.
    return web.json_response(
        {
            "platform": "gateway",
            "installed": False,
            "authenticated": False,
            "ready": bool(snapshot.get("ready")),
            "initial_setup_complete": bool(snapshot.get("initial_setup_complete")),
            "can_auto_install": False,
            "can_login": False,
            "repair_required": False,
            "docs_url": OFFICIAL_INSTALL_DOCS_URL,
            "setup_allowed": False,
            # Redacted like the rest of this block: the failure kind and probe
            # detail describe the HOST's sandbox posture (kernel knobs, errnos),
            # which is exactly the candidate/host state a non-owner must not see.
            # Kept present so the payload shape never varies by caller — a
            # non-owner already routes to the "owner must finish setup" screen.
            "sandbox_unavailable": False,
            "sandbox_failure_kind": "",
            "sandbox_detail": "",
            # Redacted for the same reason as the block above, and kept present
            # for the same shape-stability reason: only the owner can act on a
            # missing spec (the repair is an owner-gated POST). A non-owner on an
            # established install still gets the app -- the gate returns children
            # on ``initial_setup_complete`` before it consults these keys -- so
            # withholding them costs them nothing.
            "missing_agent_specs": [],
            "agent_spec_repair_error": "",
            "operation": {
                "kind": "",
                "status": "idle",
                "message": "",
                "detail": "",
                "url": "",
                "error": "",
                "code": "",
            },
        }
    )


async def api_kiro_prerequisite_install(request: web.Request) -> web.Response:
    """POST /api/kiro-prerequisite/install — start the fixed official installer."""

    denied = await _dashboard_owner_only(request)
    if denied is not None:
        return denied
    try:
        snapshot = _service(request).start_install(_caller(request))
    except PrerequisiteBusyError as exc:
        return web.json_response({"error": str(exc)}, status=409)
    return web.json_response({**snapshot, "setup_allowed": True}, status=202)


async def api_kiro_prerequisite_login(request: web.Request) -> web.Response:
    """POST /api/kiro-prerequisite/login — start Kiro device-flow login."""

    denied = await _dashboard_owner_only(request)
    if denied is not None:
        return denied
    try:
        snapshot = _service(request).start_login(_caller(request))
    except PrerequisiteBusyError as exc:
        return web.json_response({"error": str(exc)}, status=409)
    return web.json_response({**snapshot, "setup_allowed": True}, status=202)


async def api_codex_login(request: web.Request) -> web.Response:
    """POST /api/codex/login — explicitly start the local Codex login flow."""

    denied = await _dashboard_owner_only(request)
    if denied is not None:
        return denied
    state = request.app.get("state")
    sessions = getattr(state, "sessions", None)
    if getattr(sessions, "configured_provider", "codex") != "codex":
        return web.json_response(
            {
                "error": "OpenAI Codex must be selected before starting Codex sign-in.",
                "code": "codex_provider_required",
            },
            status=409,
        )

    service = _codex_login_service(request)
    try:
        service.start()
    except CodexLoginBusyError as exc:
        return web.json_response({"error": str(exc), "code": "codex_login_busy"}, status=409)

    # Reuse the last readiness observation. Starting login must return
    # immediately; probing ``codex login status`` here would race the browser
    # flow and make the explicit action appear to hang.
    cached = request.app.get("codex_readiness_cache")
    readiness = (
        cached[1]
        if isinstance(cached, tuple) and len(cached) == 2 and isinstance(cached[1], CodexReadiness)
        else CodexReadiness(False, False, "Codex readiness has not been checked yet.")
    )
    return web.json_response(
        _codex_snapshot(readiness, operation=_codex_operation_payload(service)),
        status=202,
    )


async def api_kiro_prerequisite_repair_specs(request: web.Request) -> web.Response:
    """POST /api/kiro-prerequisite/repair-specs — rewrite the managed agent specs.

    A POST rather than a flag on the status GET, because the write must be
    origin-checked and audited: ``csrf_middleware`` skips ``check_origin`` for
    ``{GET, HEAD, OPTIONS}`` and ``sel_audit_middleware`` logs only
    ``{POST, PUT, DELETE, PATCH}``, so hanging this off the status read would make
    a spec rewrite cross-site triggerable and invisible to the audit log.

    Returns 200 with the post-repair snapshot (unlike install/login's 202) because
    the repair runs to completion within the request — it is one bounded file
    write, not a long-lived background operation with progress to poll.
    """

    denied = await _dashboard_owner_only(request)
    if denied is not None:
        return denied
    try:
        snapshot = await _service(request).repair_agent_specs(_caller(request))
    except PrerequisiteBusyError as exc:
        # Coded, per the error-code contract: the dashboard renders `error`
        # verbatim into a localized UI, so `code` is what a caller can act on.
        return web.json_response({"error": str(exc), "code": "kiro_setup_busy"}, status=409)
    return web.json_response({**snapshot, "setup_allowed": True})
