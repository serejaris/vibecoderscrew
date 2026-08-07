# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
"""Tests for the in-memory compatibility skill-usage API."""

from __future__ import annotations

import json
import time

from kiro_crew.skill_usage import (
    _MAX_AGE_SECS,
    SkillUsageLedger,
)


def _ledger(tmp_path):
    return SkillUsageLedger(tmp_path / "skill-usage.json")


class TestSkillUsageLedger:
    def test_record_bumps_hits(self, tmp_path):
        led = _ledger(tmp_path)
        led.record("a")
        led.record("a")
        led.record("b")
        assert led.score("a")[0] == 2.0
        assert led.score("b")[0] == 1.0
        assert led.score("never")[0] == 0.0

    def test_score_orders_by_hits(self, tmp_path):
        led = _ledger(tmp_path)
        led.record("hot")
        led.record("hot")
        led.record("cold")
        assert led.score("hot") > led.score("cold")

    def test_recency_boost_lifts_unused(self, tmp_path):
        led = _ledger(tmp_path)
        # An unused skill with a recency boost still outranks an unused skill
        # with none (cold-start protection), but never beats a used one on hits.
        boosted = led.score("new", recency_boost=time.time())
        plain = led.score("stale", recency_boost=0.0)
        assert boosted[0] == plain[0] == 0.0
        assert boosted[1] > plain[1]

    def test_record_never_persists(self, tmp_path):
        led = _ledger(tmp_path)
        led.record("x")
        led.record("x")
        assert led.flush() is False
        assert not (tmp_path / "skill-usage.json").exists()
        led2 = _ledger(tmp_path)
        assert led2.score("x")[0] == 0.0

    def test_missing_file_is_empty(self, tmp_path):
        led = _ledger(tmp_path)  # no file yet
        assert led.score("anything")[0] == 0.0

    def test_legacy_file_is_not_read(self, tmp_path):
        (tmp_path / "skill-usage.json").write_text("{ not json ]")
        led = _ledger(tmp_path)  # must not raise
        assert led.score("anything")[0] == 0.0

    def test_legacy_file_is_ignored_even_when_valid(self, tmp_path):
        stale_ts = time.time() - _MAX_AGE_SECS - 100
        fresh_ts = time.time()
        (tmp_path / "skill-usage.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "keys": {
                        "old": {"hits": 99, "last_seen": stale_ts},
                        "new": {"hits": 1, "last_seen": fresh_ts},
                    },
                }
            )
        )
        led = _ledger(tmp_path)
        assert led.score("old")[0] == 0.0
        assert led.score("new")[0] == 0.0

    def test_flush_noop_when_clean(self, tmp_path):
        led = _ledger(tmp_path)
        assert led.flush() is False  # nothing recorded → nothing to write
