# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Tests for GET /api/telemetry/beacon — the privacy panel's opt-out state.

The endpoint backs the Settings → Privacy toggle. In this edition the outbound
boundary is hard-disabled, so ``enabled`` and ``would_send`` both stay false
even when legacy config stores ``beacon_enabled: true``. Suppressor metadata
remains in the response for compatibility and diagnostics.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from kiro_crew import beacon


def _make_app() -> web.Application:
    from kiro_crew.dashboard.handlers import api_beacon_status

    app = web.Application()
    app.router.add_get("/api/telemetry/beacon", api_beacon_status)
    return app


@pytest.fixture(autouse=True)
def _neutral_env(tmp_path, monkeypatch):
    """Keep the status contract hermetic while production telemetry is off.

    Real CI can add extra suppressors, but the hard-disabled edition boundary
    must be the reason this endpoint reports ``would_send: false``.
    """
    monkeypatch.setenv("KIROCREW_HOME", str(tmp_path))
    monkeypatch.setattr(beacon, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(beacon, "is_default_home", lambda: True)
    monkeypatch.setattr(beacon, "is_ci", lambda: False)
    monkeypatch.delenv(beacon.DISABLE_ENV, raising=False)
    # Keep the production hard-disabled boundary intact.  Re-enabling the
    # retired path here would make this status test a false positive.
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "telemetry": {
                    "beacon_enabled": True,
                    "beacon_endpoint": "https://beacon.example.test",
                }
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


async def _get(client: TestClient) -> dict:
    resp = await client.get("/api/telemetry/beacon")
    assert resp.status == 200
    return await resp.json()


class TestBeaconStatusEndpoint:
    @pytest.mark.asyncio
    async def test_vibecoderscrew_edition_reports_hard_disabled(self, _neutral_env) -> None:
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert body["enabled"] is False
        assert body["would_send"] is False
        assert body["endpoint_configured"] is False
        assert body["governance_override"] is True
        assert "VibecodersCrew" in body["reason"]

    @pytest.mark.asyncio
    async def test_stored_flag_cannot_enable_hard_disabled_runtime(self, _neutral_env) -> None:
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert body["enabled"] is False
        assert body["would_send"] is False
        assert body["endpoint_configured"] is False
        assert "VibecodersCrew" in body["reason"]
        assert body["env_override"] is False
        assert body["env_var"] == beacon.DISABLE_ENV

    @pytest.mark.asyncio
    async def test_env_override_is_flagged(self, _neutral_env, monkeypatch) -> None:
        """The env var pins the beacon off — the UI disables the toggle on this."""
        monkeypatch.setenv(beacon.DISABLE_ENV, "1")
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert body["env_override"] is True
        assert body["would_send"] is False
        assert "VibecodersCrew" in body["reason"]

    @pytest.mark.asyncio
    async def test_stored_flag_on_but_suppressed_reports_both(
        self, _neutral_env, monkeypatch
    ) -> None:
        """Legacy stored state remains visible through hard-disabled runtime."""
        monkeypatch.setattr(beacon, "is_default_home", lambda: False)
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert body["enabled"] is False
        assert body["would_send"] is False
        assert "VibecodersCrew" in body["reason"]
        # Not the env var — so the toggle stays usable.
        assert body["env_override"] is False

    @pytest.mark.asyncio
    async def test_overlay_entry_is_flagged(self, _neutral_env, monkeypatch) -> None:
        """A config.local.json entry pins the value the toggle cannot change.

        The overlay deep-merges OVER config.json, which is the file the Settings
        toggle writes — so without this flag the switch would snap back to the
        overlay's value after a successful save, with no explanation.
        """
        import json as _json

        (_neutral_env / "config.json").write_text(
            _json.dumps({"telemetry": {"beacon_enabled": False}}), encoding="utf-8"
        )
        (_neutral_env / "config.local.json").write_text(
            _json.dumps({"telemetry": {"beacon_enabled": True}}), encoding="utf-8"
        )
        monkeypatch.setattr(
            "kiro_crew.config.loader.config_dir", lambda: _neutral_env, raising=False
        )
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert body["overlay_override"] is True

    @pytest.mark.asyncio
    async def test_no_overlay_file_is_not_flagged(self, _neutral_env) -> None:
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert body["overlay_override"] is False

    @pytest.mark.asyncio
    async def test_overlay_without_the_key_is_not_flagged(self, _neutral_env, monkeypatch) -> None:
        """An overlay that sets other telemetry fields does not pin this one."""
        import json as _json

        (_neutral_env / "config.local.json").write_text(
            _json.dumps({"telemetry": {"export_interval_seconds": 30}}), encoding="utf-8"
        )
        monkeypatch.setattr(
            "kiro_crew.config.loader.config_dir", lambda: _neutral_env, raising=False
        )
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert body["overlay_override"] is False

    @pytest.mark.asyncio
    async def test_malformed_overlay_does_not_raise(self, _neutral_env, monkeypatch) -> None:
        """A diagnostic must survive a broken overlay rather than 500."""
        (_neutral_env / "config.local.json").write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(
            "kiro_crew.config.loader.config_dir", lambda: _neutral_env, raising=False
        )
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert body["overlay_override"] is False

    @pytest.mark.asyncio
    async def test_never_materializes_an_install_id(self, _neutral_env) -> None:
        """Reading the panel must not create an id for a user who never sends."""
        async with TestClient(TestServer(_make_app())) as c:
            await _get(c)
        assert not (_neutral_env / beacon.INSTALL_ID_FILE).exists()

    @pytest.mark.asyncio
    async def test_does_not_leak_the_install_id(self, _neutral_env) -> None:
        """The panel needs state, not the identifier itself."""
        async with TestClient(TestServer(_make_app())) as c:
            body = await _get(c)
        assert "install_id" not in body

    @pytest.mark.asyncio
    async def test_unreadable_config_fails_toward_off(self, _neutral_env) -> None:
        """A diagnostic must not 500, and must never claim telemetry is on."""
        with patch(
            "kiro_crew.config.loader.KiroCrewConfig.load",
            side_effect=OSError("boom"),
        ):
            async with TestClient(TestServer(_make_app())) as c:
                body = await _get(c)
        assert body["enabled"] is False
        assert body["would_send"] is False
