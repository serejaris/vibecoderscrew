# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Compatibility shim for the retired skill-usage ledger.

Skill selection is intentionally stateless with respect to usage.  The old
implementation persisted ``skill-usage.json`` under the data home, which made
ordinary skill loading create a durable activity log.  The public build keeps
the small in-memory API for callers that still import it, while all disk reads
and writes are disabled.
"""

from __future__ import annotations

import time
from pathlib import Path

# Kept for source compatibility with older integrations.  No runtime path is
# derived from this value and no file with this name is read or written.
SKILL_USAGE_FILENAME = "skill-usage.json"

_MAX_AGE_SECS = 30 * 24 * 60 * 60
_MAX_TRACKED = 1024


class SkillUsageLedger:
    """In-memory compatibility tally with persistence permanently disabled.

    ``path`` is accepted for compatibility only and is never opened, created,
    or modified.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._hits: dict[str, int] = {}
        self._last_seen: dict[str, float] = {}

    def score(self, key: str, *, recency_boost: float = 0.0) -> tuple[float, float]:
        """Return the in-memory sort key ``(hits, effective_last_seen)``."""
        hits = self._hits.get(key, 0)
        last_seen = self._last_seen.get(key, 0.0)
        return (float(hits), max(last_seen, recency_boost))

    def record(self, key: str) -> None:
        """Bump ``key`` in memory without creating a usage log."""
        if not key:
            return
        now = time.time()
        self._hits[key] = self._hits.get(key, 0) + 1
        self._last_seen[key] = now
        if len(self._hits) > _MAX_TRACKED:
            self._prune(now)

    def _prune(self, now: float) -> None:
        """Shrink to the hottest ``_MAX_TRACKED`` live keys."""
        fresh = {
            key: self._hits[key]
            for key in self._hits
            if now - self._last_seen.get(key, 0.0) <= _MAX_AGE_SECS
        }
        if len(fresh) > _MAX_TRACKED:
            kept = sorted(
                fresh,
                key=lambda key: (fresh[key], self._last_seen.get(key, 0.0)),
                reverse=True,
            )[:_MAX_TRACKED]
            fresh = {key: fresh[key] for key in kept}
        self._hits = fresh
        self._last_seen = {key: self._last_seen.get(key, 0.0) for key in fresh}

    def flush(self) -> bool:
        """Keep the legacy method callable without persisting anything."""
        return False
