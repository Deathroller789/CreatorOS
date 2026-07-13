"""Tests for Channel Intelligence V1 (Q1 outliers, Q2 titles, Q3 cadence)."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from creatoros.intelligence import IntelligenceError, analyze_channel

NOW = datetime(2026, 1, 11, tzinfo=UTC)


def _write_db(path: Path, channel: dict, videos: list[dict]) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE channels (channel_id TEXT, title TEXT, handle TEXT, "
            "url TEXT, subscriber_count INTEGER)"
        )
        conn.execute(
            "CREATE TABLE videos (video_id TEXT, channel_id TEXT, title TEXT, "
            "upload_date TEXT, view_count INTEGER, url TEXT)"
        )
        conn.execute(
            "INSERT INTO channels VALUES (:channel_id, :title, :handle, :url, "
            ":subscriber_count)",
            channel,
        )
        for v in videos:
            conn.execute(
                "INSERT INTO videos VALUES (:video_id, :channel_id, :title, "
                ":upload_date, :view_count, :url)",
                v,
            )
        conn.commit()
    finally:
        conn.close()


def _video(vid: str, upload_date: str, views: int | None, title: str) -> dict:
    return {
        "video_id": vid,
        "channel_id": "UC1",
        "title": title,
        "upload_date": upload_date,
        "view_count": views,
        "url": f"https://youtu.be/{vid}",
    }


CHANNEL = {
    "channel_id": "UC1",
    "title": "Test Channel",
    "handle": "@test",
    "url": "https://youtube.com/@test",
    "subscriber_count": 1000,
}

# Ages 10/20/30 days -> 100/50/200 views/day. Median baseline 100. Longer titles under.
VIDEOS = [
    _video("v1", "20260101", 1_000, "Short punchy title"),
    _video("v2", "20251222", 1_000, "A considerably longer and wordier video title"),
    _video("v3", "20251212", 6_000, "Big win"),
]


def _analyze(videos: list[dict], channel: dict = CHANNEL):
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "t.db"
        _write_db(db, channel, videos)
        return analyze_channel(channel["channel_id"], db_path=db, now=NOW)


class OutlierTests(unittest.TestCase):
    def test_ranking_is_sorted_by_performance_index(self) -> None:
        f = _analyze(VIDEOS)
        order = [o.performance_index for o in f.outliers.ranking]
        self.assertEqual(order, sorted(order, reverse=True))
        self.assertEqual(f.outliers.ranking[0].video_id, "v3")  # 200/100 = 2.0x
        self.assertEqual(f.outliers.ranking[-1].video_id, "v2")  # 50/100 = 0.5x

    def test_baseline_and_difference_are_derived(self) -> None:
        f = _analyze(VIDEOS)
        self.assertEqual(f.outliers.baseline_views_per_day, 100.0)
        top = f.outliers.ranking[0]
        self.assertAlmostEqual(top.views_per_day, 200.0)
        self.assertAlmostEqual(top.difference_views_per_day, 100.0)  # 200 - 100
        self.assertAlmostEqual(top.performance_index, 2.0)

    def test_fresh_video_is_flagged_recent(self) -> None:
        f = _analyze([*VIDEOS, _video("v4", "20260111", 5_000, "Today")])
        recent = {o.video_id for o in f.outliers.ranking if o.is_recent}
        self.assertIn("v4", recent)
        self.assertNotIn("v1", recent)

    def test_hidden_views_leave_the_ranking_but_not_the_channel(self) -> None:
        f = _analyze([*VIDEOS, _video("v5", "20260101", None, "Hidden")])
        self.assertNotIn("v5", {o.video_id for o in f.outliers.ranking})
        self.assertEqual(f.outliers.baseline_views_per_day, 100.0)


class TitleTests(unittest.TestCase):
    def test_above_and_below_groups_split_on_baseline(self) -> None:
        f = _analyze(VIDEOS)
        # v3 (2.0x) and v1 (1.0x) at/above baseline; v2 (0.5x) below.
        self.assertEqual(f.titles.above_n, 2)
        self.assertEqual(f.titles.below_n, 1)

    def test_title_length_comparison_is_reported_with_group_sizes(self) -> None:
        f = _analyze(VIDEOS)
        by_metric = {c.metric: c for c in f.titles.features}
        self.assertIn("title_length", by_metric)
        length = by_metric["title_length"]
        # The one below-baseline video has the long title.
        self.assertLess(length.above_mean, length.below_mean)
        self.assertEqual(length.above_n, 2)
        self.assertEqual(length.below_n, 1)

    def test_effect_size_withheld_for_small_groups(self) -> None:
        # #42: at 2 vs 1 the effect size is noise; means/difference stay, d is withheld.
        f = _analyze(VIDEOS)
        for c in f.titles.features:
            self.assertIsNone(c.effect_size)
            self.assertIsNotNone(c.difference)  # descriptive facts still reported

    def test_effect_size_reported_when_both_groups_are_adequate(self) -> None:
        # Ten videos, same age -> baseline is the median rate; five sit above, five
        # below. Titles vary in length within each group (non-zero variance), so with
        # 5 per group the effect size is estimated rather than withheld.
        videos = [
            _video(f"v{i}", "20260101", (i + 1) * 100, "word " * (i + 1))
            for i in range(10)
        ]
        f = _analyze(videos)
        length = {c.metric: c for c in f.titles.features}["title_length"]
        self.assertEqual(length.above_n, 5)
        self.assertEqual(length.below_n, 5)
        self.assertIsNotNone(length.effect_size)


class CadenceTests(unittest.TestCase):
    def test_regular_cadence_is_labelled(self) -> None:
        f = _analyze(VIDEOS)  # gaps 10, 10 -> cv 0
        self.assertEqual(f.cadence.median_interval_days, 10.0)
        self.assertEqual(f.cadence.consistency_cv, 0.0)
        self.assertEqual(f.cadence.regularity, "regular")

    def test_erratic_cadence_is_labelled(self) -> None:
        videos = [
            _video("a", "20260110", 100, "one"),  # 1 day
            _video("b", "20260109", 100, "two"),  # 2 days
            _video("c", "20251110", 100, "three"),  # 62 days -> big gap
        ]
        f = _analyze(videos)
        self.assertGreater(f.cadence.consistency_cv, 1.0)
        self.assertEqual(f.cadence.regularity, "erratic")


class ContractTests(unittest.TestCase):
    def test_every_finding_group_carries_a_sample_size_and_confidence(self) -> None:
        f = _analyze(VIDEOS)
        for group in (f.outliers, f.titles, f.cadence):
            self.assertIsInstance(group.sample_size, int)
            self.assertIn(group.confidence.level, ("low", "moderate", "reasonable"))
            self.assertTrue(group.confidence.reason)

    def test_small_sample_yields_low_confidence(self) -> None:
        f = _analyze(VIDEOS)  # n=3
        self.assertEqual(f.outliers.confidence.level, "low")

    def test_unknown_channel_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.db"
            _write_db(db, CHANNEL, VIDEOS)
            with self.assertRaises(IntelligenceError):
                analyze_channel("does-not-exist", db_path=db, now=NOW)

    def test_channel_with_no_videos_raises(self) -> None:
        with self.assertRaises(IntelligenceError):
            _analyze([])

    def test_intelligence_layer_renders_nothing(self) -> None:
        # The architectural boundary as an executable assertion: intelligence neither
        # serializes output nor depends on the reporting layer. It produces findings; a
        # renderer (separate layer) turns those into a format. No format leaks in here.
        package = Path(__file__).resolve().parent.parent / "creatoros" / "intelligence"
        forbidden = ("import json", "creatoros.reporting", "markdown")
        for source in package.glob("*.py"):
            text = source.read_text(encoding="utf-8").lower()
            for token in forbidden:
                with self.subTest(module=source.name, token=token):
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
