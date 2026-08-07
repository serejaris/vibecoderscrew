#!/usr/bin/env python3
# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Normalize and validate the checked-in third-party notice inventory.

The dependency inventory is assembled from the production dependency graphs and
the resolved Python environment by the release workflow.  License text is
copied verbatim into ``THIRD-PARTY-NOTICES``; only provenance paths are
normalized here so a local virtualenv path cannot leak into a source release.

This small finalization step is intentionally fail-closed.  It preserves the
generator's exact entry count and refuses to write a notice that still carries
an absolute developer-machine path.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_NOTICE = Path(__file__).resolve().parents[1] / "THIRD-PARTY-NOTICES"
EXPECTED_ENTRIES = 467

_ABSOLUTE_LOCAL_PATH = re.compile(r"(?m)(?<![A-Za-z0-9_])/(?:Users|home|private|tmp)/")
_PYTHON_LICENSE_PATH = re.compile(
    r"(?m)^(?P<prefix>- License file: )(?P<root>.+?/site-packages/)(?P<path>.+)$"
)


def normalize_license_paths(text: str) -> str:
    """Replace local site-packages roots with a portable provenance marker."""

    return _PYTHON_LICENSE_PATH.sub(r"\g<prefix>site-packages/\g<path>", text)


def entry_count(text: str) -> int:
    """Count dependency entries while excluding section and explanatory headings."""

    npm_start = text.index("## NPM production dependencies")
    python_start = text.index("## Python runtime dependencies")
    npm_section = text[npm_start:python_start]
    npm = re.findall(r"^## .+ v\d[^\n]*$", npm_section, flags=re.MULTILINE)
    python_section = text[python_start:]
    python = re.findall(r"^## Python runtime: .+$", python_section, flags=re.MULTILINE)
    vendored = re.findall(
        r"^## Vendored llama-cpp-python v[^\n]*$", python_section, flags=re.MULTILINE
    )
    return len(npm) + len(python) + len(vendored)


def validate(text: str) -> None:
    """Reject missing coverage or any remaining absolute local path."""

    match = re.search(r"^Total deduplicated third-party entries: (\d+)\.$", text, re.MULTILINE)
    if not match or int(match.group(1)) != EXPECTED_ENTRIES:
        actual = match.group(1) if match else "missing"
        raise ValueError(f"expected coverage header {EXPECTED_ENTRIES}, got {actual}")
    actual_entries = entry_count(text)
    if actual_entries != EXPECTED_ENTRIES:
        raise ValueError(f"expected {EXPECTED_ENTRIES} entries, counted {actual_entries}")
    leaked = _ABSOLUTE_LOCAL_PATH.search(text)
    if leaked:
        line = text.count("\n", 0, leaked.start()) + 1
        raise ValueError(f"absolute local path remains at line {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_NOTICE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true", help="validate without writing")
    args = parser.parse_args()

    if args.check:
        # Check mode is intentionally strict: it validates the checked-in
        # artifact as-is instead of normalizing a temporary copy. This keeps a
        # local-path leak fail-closed in CI/release gates.
        validate(args.input.read_text(encoding="utf-8"))
        return 0
    source = args.input.read_text(encoding="utf-8")
    normalized = normalize_license_paths(source)
    validate(normalized)
    destination = args.output or args.input
    destination.write_text(normalized, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
