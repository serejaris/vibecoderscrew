# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Regression guards for side-effect-free gateway/dashboard startup paths."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kiro_crew.config.loader import KiroCrewConfig
from kiro_crew.dashboard import handlers_system
from kiro_crew.slack.gateway import GatewayOrchestrator


def _orchestrator(*, no_dashboard: bool = True) -> GatewayOrchestrator:
    cfg = KiroCrewConfig()
    with patch.object(cfg, "load_credentials", return_value={}):
        return GatewayOrchestrator(cfg, no_dashboard=no_dashboard, no_crons=True, no_open=True)


@pytest.mark.asyncio
async def test_gateway_boot_does_not_run_legacy_egress(monkeypatch, tmp_path) -> None:
    """Boot must not invoke the old git/MCP/pip/process side effects."""
    import kiro_crew

    orch = _orchestrator()
    orch._cfg.mcp_gateway.enabled = False
    orch._init_services = MagicMock()
    orch._start_embeddings = AsyncMock()
    orch._auto_migrate_memory = AsyncMock()
    orch._init_mcp_gateway = AsyncMock()
    orch._init_cron = AsyncMock()
    orch._init_heartbeat = AsyncMock()
    orch._init_mcp_discovery = MagicMock()
    orch._init_subagents = MagicMock()
    orch._init_task_runner = MagicMock()
    orch._init_api_server = AsyncMock()
    orch._init_autonudge = AsyncMock()
    orch._check_for_updates = AsyncMock()
    orch._shutdown = AsyncMock()

    # Force the legacy update guard's old environment branch to be eligible.
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("KIROCREW_PROJECT_DIR", str(tmp_path))
    fresh_event = asyncio.Event()
    fresh_event.set()
    loop = asyncio.get_running_loop()
    with (
        patch.object(loop, "add_signal_handler"),
        patch("kiro_crew.shutdown_event", fresh_event),
        patch("kiro_crew.slack.gateway.shutdown_event", fresh_event),
        patch("kiro_crew.dashboard.handlers._bg_mcp_probe", new_callable=AsyncMock) as mcp_probe,
        patch("kiro_crew.slack.events.init_socket_mode"),
        patch("kiro_crew.slack.interactions.init"),
        patch("kiro_crew.slack.events.SeenCache"),
        patch("kiro_crew.session.cleanup_orphaned_sessions"),
        patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as child_spawn,
        patch("subprocess.run") as pip_run,
        patch("os._exit"),
        patch("resource.getrlimit", return_value=(256, 10240)),
        patch("resource.setrlimit"),
    ):
        await orch.run()

    orch._check_for_updates.assert_not_awaited()
    mcp_probe.assert_not_awaited()
    child_spawn.assert_not_awaited()
    pip_run.assert_not_called()
    # Keep the global lazy event usable for the rest of the test session.
    kiro_crew.shutdown_event.clear()


@pytest.mark.asyncio
async def test_status_route_is_cache_only(monkeypatch) -> None:
    """A forced stale update timestamp cannot make /api/status fetch or spawn."""

    class _Crons:
        @staticmethod
        def status() -> dict[str, object]:
            return {}

    class _State:
        start_time = time.time()
        _owner_hash = "owner-hash"
        messages_received = 0
        _update_progress: dict[str, object] = {}
        crons = _Crons()

        @staticmethod
        def status_snapshot(**kwargs: object) -> dict[str, object]:
            return {"update_available": bool(kwargs.get("update_available"))}

    state = _State()
    request = SimpleNamespace(app={"state": state})
    status = SimpleNamespace(
        active=False,
        expires_at_iso="",
        remaining_secs=0,
        permanent=False,
    )
    context = SimpleNamespace(
        telemetry=SimpleNamespace(frontend_rum_config=lambda: None),
    )

    monkeypatch.setattr(handlers_system, "_STATIC_SYSTEM_INFO", None)
    monkeypatch.setattr(handlers_system, "_yolo_duration_fields", lambda: ("6h", True))
    monkeypatch.setattr(
        handlers_system, "safety_override", lambda: SimpleNamespace(status=lambda: status)
    )
    monkeypatch.setattr(handlers_system, "current_context", lambda: context)

    with (
        patch("kiro_crew.dashboard.handlers.updates._last_update_check", 0.0),
        patch(
            "kiro_crew.dashboard.handlers.updates._do_update_check",
            new_callable=AsyncMock,
        ) as update_check,
        patch("subprocess.check_output", side_effect=AssertionError("status spawned a command")),
        patch("asyncio.create_subprocess_exec", side_effect=AssertionError("status spawned git")),
    ):
        response = await handlers_system.api_status(request)

    assert response.status == 200
    update_check.assert_not_awaited()
