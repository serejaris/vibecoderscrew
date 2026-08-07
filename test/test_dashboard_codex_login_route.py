# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Regression coverage for the Codex prerequisite route wiring."""

from __future__ import annotations

from aiohttp import web

from kiro_crew.dashboard import handlers


def test_codex_login_handler_export_builds_dashboard_route_table() -> None:
    """Dashboard startup can register the Codex login route.

    ``dashboard.server.start_dashboard`` wires this exact route during boot.
    Keep the small route-table construction here so a handler moved to a
    submodule cannot silently make every fresh gateway exit before onboarding.
    """
    assert callable(handlers.api_codex_login)

    app = web.Application()
    app.router.add_post("/api/codex/login", handlers.api_codex_login)

    routes = {(route.method, route.resource.canonical) for route in app.router.routes()}
    assert ("POST", "/api/codex/login") in routes
