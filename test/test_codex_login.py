# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Explicit Codex login action contract tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


@pytest.mark.asyncio
async def test_codex_login_service_uses_fixed_argv_and_reports_success() -> None:
    from kiro_crew.providers.codex import CodexLoginService

    process = SimpleNamespace(
        pid=1234,
        returncode=0,
        communicate=AsyncMock(return_value=(b"Opened browser\n", b"")),
    )
    spawn = AsyncMock(return_value=process)
    service = CodexLoginService(command="/usr/local/bin/codex", timeout_secs=5)

    with patch("kiro_crew.providers.codex.create_subprocess_limited", spawn):
        operation = service.start()
        await service.wait()

    assert operation.status == "running"
    spawn.assert_awaited_once()
    args, kwargs = spawn.await_args
    assert args == ("/usr/local/bin/codex", "login")
    assert "shell" not in kwargs
    assert service.snapshot().status == "succeeded"


@pytest.mark.asyncio
async def test_codex_login_service_reports_timeout_code_and_kills_process() -> None:
    from kiro_crew.providers.codex import CodexLoginService

    async def never_finishes() -> tuple[bytes, bytes]:
        await asyncio.Event().wait()
        return b"", b""

    process = SimpleNamespace(
        pid=4321,
        returncode=None,
        communicate=never_finishes,
    )
    service = CodexLoginService(command="codex", timeout_secs=0.001)

    with (
        patch(
            "kiro_crew.providers.codex.create_subprocess_limited", AsyncMock(return_value=process)
        ),
        patch(
            "kiro_crew.providers.codex.platform_compat.kill_process_tree_async", AsyncMock()
        ) as kill,
    ):
        service.start()
        await service.wait()

    assert service.snapshot().status == "failed"
    assert service.snapshot().code == "codex_login_timeout"
    kill.assert_awaited()


@pytest.mark.asyncio
async def test_codex_login_endpoint_is_owner_gated_and_starts_only_fixed_command() -> None:
    from kiro_crew.dashboard.handlers.kiro_prerequisite import api_codex_login
    from kiro_crew.providers.codex import CodexLoginService

    process = SimpleNamespace(
        pid=777,
        returncode=None,
        communicate=AsyncMock(side_effect=asyncio.CancelledError),
    )
    service = CodexLoginService(command="/tmp/codex-test")

    @web.middleware
    async def identity(request: web.Request, handler):
        request["user"] = "owner"
        request["app"] = ""
        return await handler(request)

    app = web.Application(middlewares=[identity])
    app["state"] = SimpleNamespace(
        owner_id="owner", sessions=SimpleNamespace(configured_provider="codex")
    )
    app["codex_login_service"] = service
    app.router.add_post("/api/codex/login", api_codex_login)

    with (
        patch(
            "kiro_crew.providers.codex.create_subprocess_limited",
            AsyncMock(return_value=process),
        ) as spawn,
        patch(
            "kiro_crew.providers.codex.platform_compat.kill_process_tree_async",
            AsyncMock(),
        ),
    ):
        async with TestClient(TestServer(app)) as client:
            response = await client.post("/api/codex/login")
            payload = await response.json()
            assert response.status == 202
            assert payload["operation"]["status"] == "running"
            await asyncio.sleep(0)
            args, kwargs = spawn.await_args
            assert args == ("/tmp/codex-test", "login")
            assert "shell" not in kwargs
        await service.close()


@pytest.mark.asyncio
async def test_codex_status_polls_operation_without_rechecking_until_completion() -> None:
    from kiro_crew.dashboard.handlers.kiro_prerequisite import (
        api_kiro_prerequisite_status,
    )
    from kiro_crew.providers.codex import (
        CodexLoginOperation,
        CodexLoginService,
        CodexReadiness,
    )

    service = CodexLoginService(command="/tmp/codex-test")
    service._operation = CodexLoginOperation(status="running", message="Codex sign-in is running.")

    @web.middleware
    async def identity(request: web.Request, handler):
        request["user"] = "owner"
        request["app"] = ""
        return await handler(request)

    app = web.Application(middlewares=[identity])
    app["state"] = SimpleNamespace(
        owner_id="owner", sessions=SimpleNamespace(configured_provider="codex")
    )
    app["codex_login_service"] = service
    app["codex_readiness_cache"] = (0.0, CodexReadiness(True, False, "cached"))
    app.router.add_get("/api/kiro-prerequisite", api_kiro_prerequisite_status)

    completed_readiness = CodexReadiness(True, False, "Not logged in")
    with patch(
        "kiro_crew.dashboard.kiro_readiness.probe_codex_readiness",
        AsyncMock(return_value=completed_readiness),
    ) as probe:
        async with TestClient(TestServer(app)) as client:
            running_response = await client.get("/api/kiro-prerequisite")
            running_payload = await running_response.json()
            assert running_response.status == 200
            assert running_payload["operation"]["status"] == "running"
            assert probe.await_count == 0

            service._operation = CodexLoginOperation(
                status="succeeded", message="Codex sign-in finished."
            )
            # ``CodexLoginService._notify_finished`` clears this cache in the
            # real flow; model that transition directly in the seam test.
            app["codex_readiness_cache"] = None

            completed_response = await client.get("/api/kiro-prerequisite")
            completed_payload = await completed_response.json()
            assert completed_response.status == 200
            assert completed_payload["operation"]["status"] == "succeeded"
            assert probe.await_count == 1

            repeated_response = await client.get("/api/kiro-prerequisite")
            repeated_payload = await repeated_response.json()
            assert repeated_response.status == 200
            assert repeated_payload["operation"]["status"] == "succeeded"
            assert probe.await_count == 1
