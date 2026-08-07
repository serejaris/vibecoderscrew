# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Source-only distribution boundaries.

The public fork ships source and package artifacts.  GitHub Actions publishing,
desktop signing, and remote release feeds remain outside that boundary, so
contract tests that inspect those lanes use hermetic fixtures when present and
skip against this checkout.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_github_actions_workflows_are_absent() -> None:
    """A source-only checkout must not carry executable release workflows."""
    assert not (ROOT / ".github" / "workflows").exists()
