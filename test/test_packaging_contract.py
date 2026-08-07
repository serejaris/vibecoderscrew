# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Source distribution hygiene contracts."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sdist_bytecode_exclusions_follow_recursive_skill_include() -> None:
    """The manifest must not re-add deployment skill caches after pruning."""
    lines = (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
    include = lines.index("recursive-include src/kiro_crew/deploy/skills *")
    excludes = [
        lines.index("global-exclude __pycache__"),
        lines.index("global-exclude *.py[cod]"),
    ]
    assert all(include < exclude for exclude in excludes)


def test_notice_generator_is_shipped_and_check_mode_is_fail_closed() -> None:
    """The legal source generator ships with the sdist and validates in place."""
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "include scripts/generate_third_party_notices.py" in manifest
    generator = ROOT / "scripts/generate_third_party_notices.py"
    source = generator.read_text(encoding="utf-8")
    assert "if args.check:" in source
    assert 'validate(args.input.read_text(encoding="utf-8"))' in source


def test_wheel_bytecode_exclusions_cover_nested_package_data() -> None:
    """Wheel package-data rules cover both cache directories and bytecode."""
    text = (ROOT / "setup.cfg").read_text(encoding="utf-8")
    assert "__pycache__/*" in text
    assert "*/__pycache__/*" in text
    assert "*.py[cod]" in text
    assert "*/*.py[cod]" in text


def test_third_party_notice_is_portable_and_keeps_exact_coverage() -> None:
    """Legal provenance must not embed a developer checkout path."""
    notice = (ROOT / "THIRD-PARTY-NOTICES").read_text(encoding="utf-8")
    assert "/Users/" not in notice
    assert "/home/" not in notice
    assert "Total deduplicated third-party entries: 467." in notice
    assert "scripts/generate_third_party_notices.py" in notice
