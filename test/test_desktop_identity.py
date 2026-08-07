# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Focused identity checks for the desktop shell and computer-use floor."""

from __future__ import annotations

import pytest

from kiro_crew.cli_desktop import PRODUCT_NAMES
from kiro_crew.computer_use.policy import denied_rule_for, title_is_denied
from kiro_crew.computer_use.types import AppRef


def test_desktop_log_product_names_match_electron_builds() -> None:
    assert PRODUCT_NAMES == ("VibecodersCrew", "VibecodersCrew Nightly")


@pytest.mark.parametrize(
    "bundle_id",
    (
        "dev.serejaris.vibecoderscrew",
        "dev.serejaris.vibecoderscrew.nightly",
        "dev.serejaris.vibecoderscrew.helper",
    ),
)
def test_computer_use_denies_vibecoders_bundle_ids(bundle_id: str) -> None:
    app = AppRef(name="Electron", pid=1, bundle_id=bundle_id)
    assert denied_rule_for(app) is not None


@pytest.mark.parametrize(
    "bundle_id",
    (
        "tech.serejaris.vibecoderscrew",
        "dev.serejaris.kirocrew.codex",
        "dev.serejaris.kirocrew.codex.nightly",
        "com.amazon.kiro.crew",
        "dev.kiro.crew",
    ),
)
def test_computer_use_keeps_legacy_bundle_ids_denied(bundle_id: str) -> None:
    app = AppRef(name="Electron", pid=1, bundle_id=bundle_id)
    assert denied_rule_for(app) is not None


@pytest.mark.parametrize(
    "title",
    (
        "Kiro Crew",
        "(2) Kiro Crew — Settings",
        "KiroCrew",
        "Artifacts — KiroCrew",
    ),
)
def test_computer_use_keeps_legacy_titles_denied(title: str) -> None:
    app = AppRef(
        name="Google Chrome",
        pid=1,
        bundle_id="com.google.Chrome",
        window_title=title,
    )
    assert denied_rule_for(app) is not None
    assert title_is_denied(title)


def test_computer_use_denies_vibecoders_browser_tab_title() -> None:
    app = AppRef(
        name="Google Chrome",
        pid=1,
        bundle_id="com.google.Chrome",
        window_title="(2) Vibecoders Crew — Settings",
    )
    assert denied_rule_for(app) is not None
    assert title_is_denied(app.window_title)
