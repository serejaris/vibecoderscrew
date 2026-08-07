# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Tests for explicit dashboard browser opening.

Covers:
- DashboardConfig.auto_open_browser default and JSON loading
- GatewayOrchestrator stores browser flags
- run_gateway passes browser flags to orchestrator
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kiro_crew.cli import _resolve_gateway_args
from kiro_crew.config.loader import DashboardConfig, KiroCrewConfig


def _load_from_raw_string(content: str) -> KiroCrewConfig:
    """Write raw string content to a temp file and load."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(content)
        tmp = Path(f.name)

    with patch("kiro_crew.config.loader.config_path", return_value=tmp):
        return KiroCrewConfig.load()


class TestAutoOpenBrowserConfig:
    """Tests for dashboard.auto_open_browser config field."""

    def test_default_is_false(self) -> None:
        """DashboardConfig defaults auto_open_browser to False."""
        cfg = DashboardConfig()
        assert cfg.auto_open_browser is False

    def test_from_json_false(self) -> None:
        """Loading config with auto_open_browser=false reads the value."""
        content = json.dumps({"dashboard": {"auto_open_browser": False}})
        cfg = _load_from_raw_string(content)
        assert cfg.dashboard.auto_open_browser is False

    def test_from_json_true(self) -> None:
        """Loading config with auto_open_browser=true reads the value."""
        content = json.dumps({"dashboard": {"auto_open_browser": True}})
        cfg = _load_from_raw_string(content)
        assert cfg.dashboard.auto_open_browser is True

    def test_missing_key_defaults_false(self) -> None:
        """Missing auto_open_browser key defaults to False."""
        content = json.dumps({"dashboard": {}})
        cfg = _load_from_raw_string(content)
        assert cfg.dashboard.auto_open_browser is False

    def test_roundtrip_serialization(self) -> None:
        """auto_open_browser survives save/load roundtrip."""
        cfg = KiroCrewConfig()
        cfg.dashboard.auto_open_browser = False
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            tmp = Path(f.name)
        with patch("kiro_crew.config.loader.config_path", return_value=tmp):
            cfg.save()
            loaded = KiroCrewConfig.load()
        assert loaded.dashboard.auto_open_browser is False


class TestNoOpenCliFlag:
    """Tests for explicit browser flag propagation."""

    def test_orchestrator_stores_no_open_true(self) -> None:
        """GatewayOrchestrator stores no_open=True."""
        from kiro_crew.slack.gateway import GatewayOrchestrator

        cfg = KiroCrewConfig()
        with patch.object(cfg, "load_credentials", return_value={}):
            orch = GatewayOrchestrator(cfg, no_open=True)
        assert orch._no_open is True

    def test_orchestrator_stores_no_open_false_by_default(self) -> None:
        """GatewayOrchestrator defaults no_open/open_browser to False."""
        from kiro_crew.slack.gateway import GatewayOrchestrator

        cfg = KiroCrewConfig()
        with patch.object(cfg, "load_credentials", return_value={}):
            orch = GatewayOrchestrator(cfg)
        assert orch._no_open is False
        assert orch._open_browser is False

    def test_orchestrator_stores_open_browser_true(self) -> None:
        """GatewayOrchestrator accepts the explicit browser action."""
        from kiro_crew.slack.gateway import GatewayOrchestrator

        cfg = KiroCrewConfig()
        with patch.object(cfg, "load_credentials", return_value={}):
            orch = GatewayOrchestrator(cfg, open_browser=True)
        assert orch._open_browser is True

    def test_default_startup_does_not_request_browser(self) -> None:
        """Default startup leaves webbrowser.open untouched."""
        from kiro_crew.slack.gateway import GatewayOrchestrator

        cfg = KiroCrewConfig()
        with patch.object(cfg, "load_credentials", return_value={}):
            orch = GatewayOrchestrator(cfg)
        with patch("kiro_crew.slack.gateway.webbrowser.open") as browser_open:
            assert orch._browser_open_requested() is False
            browser_open.assert_not_called()

    def test_cli_open_is_the_explicit_opt_in(self) -> None:
        args = type(
            "Args",
            (),
            {
                "port": None,
                "json_ready": False,
                "approval": None,
                "no_open": False,
                "open_browser": True,
                "test_mode": False,
                "slack_only": False,
                "no_crons": False,
            },
        )()
        assert _resolve_gateway_args(args)["open_browser"] is True

    def test_test_mode_forces_browser_closed(self) -> None:
        args = type(
            "Args",
            (),
            {
                "port": None,
                "json_ready": False,
                "approval": None,
                "no_open": False,
                "open_browser": True,
                "test_mode": True,
                "slack_only": False,
                "no_crons": False,
            },
        )()
        resolved = _resolve_gateway_args(args)
        assert resolved["no_open"] is True
        assert resolved["open_browser"] is False

    @pytest.mark.asyncio
    async def test_run_gateway_passes_browser_flags(self) -> None:
        """run_gateway forwards both browser flags to GatewayOrchestrator."""
        from kiro_crew.slack.gateway import run_gateway

        cfg = KiroCrewConfig()
        with patch("kiro_crew.slack.gateway.GatewayOrchestrator") as mock_orch_cls:
            mock_orch = MagicMock()
            mock_orch.run = AsyncMock()
            mock_orch_cls.return_value = mock_orch
            await run_gateway(cfg, no_open=True, open_browser=True)
            mock_orch_cls.assert_called_once_with(
                cfg,
                no_dashboard=False,
                no_crons=False,
                no_open=True,
                open_browser=True,
                port_override=None,
                json_ready=False,
                approval_mode=None,
                test_mode=False,
            )
