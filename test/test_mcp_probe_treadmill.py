# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Regression tests for the cache-only MCP read endpoints.

``GET /api/mcp`` and ``GET /api/mcp/probe`` are polled while the dashboard
mounts. They must read config/cache data only, even when the cache is stale or
the configured server list changes. Live stdio/HTTP discovery belongs to the
explicit ``POST /api/mcp/probe`` action.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest

from kiro_crew.dashboard.handlers import mcp as mcp_mod
from kiro_crew.mcp_discovery import McpServerInfo


def _request(state) -> object:
    """Minimal stand-in for the aiohttp request the handler reads."""

    class _App(dict):
        pass

    class _Req:
        def __init__(self, app):
            self.app = app

    app = _App()
    app["state"] = state
    return _Req(app)


class _State:
    def __init__(self) -> None:
        self._background_tasks: set = set()


def _arrange(monkeypatch, tmp_path, servers, cache):
    """Point the handler at a synthetic server list and a warm probe cache."""
    import kiro_crew.mcp_discovery as disc

    monkeypatch.setattr(disc, "list_servers", lambda *a, **k: list(servers))
    # No mcp.json on disk: the disabled/kirocrewManaged overlay is a no-op, so
    # `disabled` comes purely from the McpServerInfo rows above.
    monkeypatch.setattr(mcp_mod, "_GLOBAL_MCP_JSON", tmp_path / "absent.json")
    monkeypatch.setattr(mcp_mod, "_kirocrew_mcp_json", lambda: tmp_path / "absent-kc.json")
    monkeypatch.setattr(mcp_mod, "_mcp_probe_cache", list(cache))
    # Warm cache: the TTL branch must NOT be the thing that triggers a reprobe.
    monkeypatch.setattr(mcp_mod, "_mcp_probe_ts", time.time())
    monkeypatch.setattr(mcp_mod, "_mcp_probe_in_progress", False)

    probe = AsyncMock(return_value=None)
    monkeypatch.setattr(mcp_mod, "_bg_mcp_probe", probe)
    return probe


class TestDisabledServerDoesNotDefeatProbeCache:
    @pytest.mark.asyncio
    async def test_disabled_server_does_not_force_a_reprobe(self, monkeypatch, tmp_path) -> None:
        """A disabled row absent from the cache must not re-arm the probe.

        Reverted (the check iterating every server rather than only probeable
        ones), this schedules a background probe on a warm cache.
        """
        servers = [
            McpServerInfo(name="enabled-one", command="/bin/true", status="ok"),
            McpServerInfo(name="turned-off", command="/bin/true", disabled=True),
        ]
        # probe_all() would only ever have returned the enabled row.
        cache = [{"name": "enabled-one", "status": "ok", "tools": [], "error": ""}]
        probe = _arrange(monkeypatch, tmp_path, servers, cache)

        state = _State()
        await mcp_mod.api_mcp_servers(_request(state))

        probe.assert_not_awaited()
        assert not state._background_tasks
        assert mcp_mod._mcp_probe_in_progress is False

    @pytest.mark.asyncio
    async def test_new_enabled_server_does_not_force_a_reprobe(self, monkeypatch, tmp_path) -> None:
        """A changed configured list still leaves the default GET side-effect free."""
        servers = [
            McpServerInfo(name="enabled-one", command="/bin/true", status="ok"),
            McpServerInfo(name="just-installed", command="/bin/true"),
        ]
        cache = [{"name": "enabled-one", "status": "ok", "tools": [], "error": ""}]
        probe = _arrange(monkeypatch, tmp_path, servers, cache)

        state = _State()
        await mcp_mod.api_mcp_servers(_request(state))

        probe.assert_not_awaited()
        assert not state._background_tasks
        assert mcp_mod._mcp_probe_in_progress is False

    @pytest.mark.asyncio
    async def test_stale_probe_cache_does_not_spawn_a_probe(self, monkeypatch, tmp_path) -> None:
        """The cached probe endpoint returns stale data without side effects."""
        servers = [McpServerInfo(name="enabled-one", command="/bin/true")]
        probe = _arrange(monkeypatch, tmp_path, servers, [])
        monkeypatch.setattr(mcp_mod, "_mcp_probe_ts", 0.0)

        response = await mcp_mod.api_mcp_probe_cached(_request(_State()))

        assert response.status == 200
        probe.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disabled_row_is_still_returned_to_the_ui(self, monkeypatch, tmp_path) -> None:
        """Skipping disabled rows in the freshness check must not hide them.

        The row still has to reach the response, otherwise the fix would trade
        the spawn treadmill for a missing table entry.
        """
        servers = [
            McpServerInfo(name="enabled-one", command="/bin/true", status="ok"),
            McpServerInfo(name="turned-off", command="/bin/true", disabled=True),
        ]
        cache = [{"name": "enabled-one", "status": "ok", "tools": [], "error": ""}]
        _arrange(monkeypatch, tmp_path, servers, cache)

        resp = await mcp_mod.api_mcp_servers(_request(_State()))

        import json as _json

        rows = _json.loads(resp.text or "[]")
        names = [r["name"] for r in rows]
        assert "turned-off" in names, "a disabled server must still render a row"
        assert "enabled-one" in names
