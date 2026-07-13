"""Tests for Channel Intelligence (performance, feature groups, corpus, cadence)."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from creatoros.intelligence import IntelligenceError, analyze_channel

NOW = datetime(2026, 1, 11, tzinfo=UTC)


def _write_db(
    path: Path,
    channel: dict,
    videos: list[dict],
    transcripts: dict[str, str] | None = None,
) -> None:
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
        conn.execute("CREATE TABLE transcripts (video_id TEXT, text TEXT)")
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
        for video_id, text in (transcripts or {}).items():
            conn.execute("INSERT INTO transcripts VALUES (?, ?)", (video_id, text))
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


def _analyze(videos: list[dict], channel: dict = CHANNEL, transcripts=None):
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "t.db"
        _write_db(db, channel, videos, transcripts)
        return analyze_channel(channel["channel_id"], db_path=db, now=NOW)


def _feature_group(findings, category: str):
    return next(g for g in findings.feature_groups if g.category == category)


def _corpus_group(findings, label: str):
    return next(g for g in findings.corpus_groups if g.label == label)


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
        self.assertEqual(f.outliers.baseline_basis_n, 3)
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


class FeatureGroupTests(unittest.TestCase):
    def test_title_family_is_discovered_and_split_on_baseline(self) -> None:
        f = _analyze(VIDEOS)
        title = _feature_group(f, "title")
        # v3 (2.0x) and v1 (1.0x) at/above baseline; v2 (0.5x) below.
        self.assertEqual(title.above_n, 2)
        self.assertEqual(title.below_n, 1)
        self.assertEqual(title.label, "Title evidence")

    def test_title_length_comparison_is_reported_with_group_sizes(self) -> None:
        f = _analyze(VIDEOS)
        by_metric = {c.metric: c for c in _feature_group(f, "title").features}
        self.assertIn("title_length", by_metric)
        length = by_metric["title_length"]
        # The one below-baseline video has the long title.
        self.assertLess(length.above_mean, length.below_mean)
        self.assertEqual(length.above_n, 2)
        self.assertEqual(length.below_n, 1)

    def test_non_informative_comparisons_are_dropped(self) -> None:
        # Every title here has a colon and no question mark, so title_has_colon and
        # title_has_question are constant across the split — no signal, so they are not
        # reported (Part D), while title_length (which varies) is.
        videos = [
            _video("v1", "20260101", 1_000, "Alpha: short"),
            _video("v2", "20251222", 1_000, "Beta: a much much longer title here"),
            _video("v3", "20251212", 6_000, "Gamma: win"),
        ]
        metrics = {c.metric for c in _feature_group(_analyze(videos), "title").features}
        self.assertIn("title_length", metrics)
        self.assertNotIn("title_has_colon", metrics)
        self.assertNotIn("title_has_question", metrics)

    def test_effect_size_withheld_for_small_groups(self) -> None:
        # #42: at 2 vs 1 the effect size is noise; means/difference stay, d is withheld.
        f = _analyze(VIDEOS)
        for c in _feature_group(f, "title").features:
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
        length = {
            c.metric: c for c in _feature_group(_analyze(videos), "title").features
        }["title_length"]
        self.assertEqual(length.above_n, 5)
        self.assertEqual(length.below_n, 5)
        self.assertIsNotNone(length.effect_size)


class CorpusTests(unittest.TestCase):
    def test_recurring_title_phrase_is_surfaced(self) -> None:
        # "scary stories" recurs across four of five titles -> corpus evidence.
        videos = [
            _video("v1", "20260101", 1_000, "Scary stories one"),
            _video("v2", "20251222", 1_000, "Scary stories two"),
            _video("v3", "20251212", 1_000, "Scary stories three"),
            _video("v4", "20251202", 1_000, "Scary stories four"),
            _video("v5", "20251122", 1_000, "Something completely different"),
        ]
        phrases = {
            p.text
            for p in _corpus_group(_analyze(videos), "Recurring title phrases").phrases
        }
        self.assertIn("scary stories", phrases)

    def test_transcript_openings_become_corpus_evidence(self) -> None:
        transcripts = {
            v["video_id"]: "welcome back everyone to the channel" for v in VIDEOS
        }
        f = _analyze(VIDEOS, transcripts=transcripts)
        openings = _corpus_group(f, "Recurring openings")
        self.assertEqual(openings.basis_n, 3)
        self.assertTrue(any("welcome back" in p.text for p in openings.phrases))
        # Fewer than the full sample of videos carry text -> the shortfall is stated.
        self.assertIsNone(openings.coverage_note)  # here all 3 have transcripts

    def test_absent_transcripts_yield_no_corpus_group(self) -> None:
        # No transcripts at all -> the transcript-based families simply do not appear
        # (ADR-009: quiet absence, never an empty or invented section).
        f = _analyze(VIDEOS)
        labels = {g.label for g in f.corpus_groups}
        self.assertNotIn("Recurring openings", labels)
        self.assertNotIn("Recurring spoken phrases", labels)


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
        groups = [f.outliers, f.cadence, *f.feature_groups, *f.corpus_groups]
        for group in groups:
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
