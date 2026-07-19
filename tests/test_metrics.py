"""Tests for the derived-metrics engine and the v1 metrics."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path

from creatoros.metrics import Metric, MetricError, compute, metric, registry

NOW = datetime(2026, 1, 11, tzinfo=UTC)
CHANNEL = {"channel_id": "UC123", "title": "Test Channel"}


def _video(video_id: str, upload_date: str, view_count: int | None, title: str) -> dict:
    return {
        "video_id": video_id,
        "upload_date": upload_date,
        "view_count": view_count,
        "title": title,
    }


# 10, 20 and 30 days old at NOW -> 100, 50 and 200 views/day. Median baseline: 100.
VIDEOS = [
    _video("v1", "20260101", 1_000, "Ten days old"),
    _video("v2", "20251222", 1_000, "Twenty days old"),
    _video("v3", "20251212", 6_000, "Thirty days old and over-performing"),
]


class RegistryTests(unittest.TestCase):
    def test_importing_the_package_populates_the_registry(self) -> None:
        # The explicit import list in creatoros/metrics/__init__.py registers every
        # active metric. A new metric is one function plus one import line —
        # explicit registration, not filesystem auto-discovery (ADR-006).
        self.assertLessEqual(
            {
                "upload_age_days",
                "views_per_day",
                "performance_index",
                "title_length",
                "title_word_count",
                "median_views_per_day",
                "median_upload_interval_days",
                "max_upload_interval_days",
                "upload_interval_cv",
            },
            set(registry()),
        )

    def test_every_metric_declares_a_unit_and_a_scope(self) -> None:
        for name, m in registry().items():
            with self.subTest(metric=name):
                self.assertTrue(m.unit, f"{name} has no unit")
                self.assertIn(m.scope, ("video", "channel"))

    def test_category_filter_returns_only_that_family(self) -> None:
        title = registry(category="title")
        # Every returned metric is tagged "title"...
        self.assertTrue(title)
        for name, m in title.items():
            self.assertEqual(m.category, "title", name)
        # ...and it includes both the original and the new structural title metrics,
        # so Q2 picks them up by category without naming them.
        self.assertLessEqual(
            {
                "title_length",
                "title_word_count",
                "title_has_number",
                "title_caps_ratio",
            },
            set(title),
        )
        # A performance metric is not a title metric.
        self.assertNotIn("performance_index", title)

    def test_parameters_must_match_declared_dependencies(self) -> None:
        with self.assertRaises(MetricError):

            @metric(scope="video", unit="ratio", depends_on=("view_count",))
            def typo(view_counts: int) -> int:  # pragma: no cover — never registered
                return view_counts

    def test_duplicate_metric_names_are_rejected(self) -> None:
        with self.assertRaises(MetricError):

            @metric(scope="video", unit="views/day", depends_on=("view_count",))
            def views_per_day(view_count: int) -> int:  # pragma: no cover
                return view_count

    def test_metrics_never_reach_for_the_database(self) -> None:
        # The architectural rule (ADR-006) as an executable assertion: nothing in this
        # layer may touch SQLite. Metrics receive plain values.
        package = Path(__file__).resolve().parent.parent / "creatoros" / "metrics"
        for source in package.glob("*.py"):
            with self.subTest(module=source.name):
                self.assertNotIn("sqlite3", source.read_text(encoding="utf-8"))


class MetricTests(unittest.TestCase):
    def test_views_per_day_is_age_normalized(self) -> None:
        derived = compute(CHANNEL, VIDEOS, now=NOW)
        self.assertEqual(derived.videos["v1"]["upload_age_days"], 10.0)
        self.assertAlmostEqual(derived.videos["v1"]["views_per_day"], 100.0)
        self.assertAlmostEqual(derived.videos["v2"]["views_per_day"], 50.0)

    def test_views_per_day_floors_the_age_of_a_brand_new_video(self) -> None:
        fresh = [_video("v9", "20260111", 5_000, "Published today")]
        derived = compute(CHANNEL, fresh, now=NOW)
        self.assertEqual(derived.videos["v9"]["upload_age_days"], 0.0)
        self.assertEqual(derived.videos["v9"]["views_per_day"], 5_000.0)

    def test_unparseable_upload_date_yields_none(self) -> None:
        derived = compute(CHANNEL, [_video("v9", "yesterday", 10, "Bad date")], now=NOW)
        self.assertIsNone(derived.videos["v9"]["upload_age_days"])
        self.assertIsNone(derived.videos["v9"]["views_per_day"])

    def test_baseline_is_the_median_not_the_mean(self) -> None:
        viral = [*VIDEOS[:2], _video("v3", "20251212", 600_000, "Viral")]
        derived = compute(CHANNEL, viral, now=NOW)
        # Mean views/day would be ~6_716; the median ignores the outlier.
        self.assertEqual(derived.channel["median_views_per_day"], 100.0)

    def test_performance_index_is_a_multiple_of_the_channel_baseline(self) -> None:
        derived = compute(CHANNEL, VIDEOS, now=NOW)
        self.assertEqual(derived.channel["median_views_per_day"], 100.0)
        self.assertAlmostEqual(derived.videos["v3"]["performance_index"], 2.0)
        self.assertAlmostEqual(derived.videos["v1"]["performance_index"], 1.0)
        self.assertAlmostEqual(derived.videos["v2"]["performance_index"], 0.5)

    def test_title_metrics(self) -> None:
        derived = compute(CHANNEL, VIDEOS, now=NOW)
        self.assertEqual(derived.videos["v1"]["title_length"], len("Ten days old"))
        self.assertEqual(derived.videos["v1"]["title_word_count"], 3)

    def test_title_structure_evidence_metrics(self) -> None:
        videos = [
            _video("a", "20260101", 100, "5 Ways to WIN: The Guide (2026)"),
            _video("b", "20260101", 100, "why did this happen?"),
            _video("c", "20260101", 100, "plain title"),
        ]
        d = compute(CHANNEL, videos, now=NOW).videos
        # "5 Ways to WIN: The Guide (2026)"
        self.assertEqual(d["a"]["title_has_number"], 1)
        self.assertEqual(d["a"]["title_starts_with_number"], 1)
        self.assertEqual(d["a"]["title_has_colon"], 1)
        self.assertEqual(d["a"]["title_has_brackets"], 1)
        self.assertEqual(d["a"]["title_has_question"], 0)
        # "why did this happen?"
        self.assertEqual(d["b"]["title_has_question"], 1)
        self.assertEqual(d["b"]["title_starts_with_number"], 0)
        # "plain title" — all lowercase, no structure
        self.assertEqual(d["c"]["title_has_number"], 0)
        self.assertEqual(d["c"]["title_caps_ratio"], 0.0)

    def test_caps_ratio_is_none_without_letters(self) -> None:
        d = compute(
            CHANNEL, [_video("n", "20260101", 100, "12345 !!!")], now=NOW
        ).videos
        self.assertIsNone(d["n"]["title_caps_ratio"])


class CadenceTests(unittest.TestCase):
    def test_median_and_max_interval_over_regular_uploads(self) -> None:
        # VIDEOS are 10, 20, 30 days old -> gaps of 10 and 10 days.
        derived = compute(CHANNEL, VIDEOS, now=NOW)
        self.assertEqual(derived.channel["median_upload_interval_days"], 10.0)
        self.assertEqual(derived.channel["max_upload_interval_days"], 10.0)

    def test_max_interval_finds_the_longest_dry_spell(self) -> None:
        # Ages 5, 10, 40 days -> gaps of 30 (the dry spell) and 5.
        videos = [
            _video("a", "20260106", 100, "5 days old"),
            _video("b", "20260101", 100, "10 days old"),
            _video("c", "20251202", 100, "40 days old"),
        ]
        derived = compute(CHANNEL, videos, now=NOW)
        self.assertEqual(derived.channel["max_upload_interval_days"], 30.0)
        self.assertEqual(derived.channel["median_upload_interval_days"], 17.5)

    def test_cv_is_zero_for_perfectly_regular_cadence(self) -> None:
        derived = compute(CHANNEL, VIDEOS, now=NOW)  # gaps 10, 10
        self.assertEqual(derived.channel["upload_interval_cv"], 0.0)

    def test_cv_is_positive_for_erratic_cadence(self) -> None:
        videos = [
            _video("a", "20260106", 100, "5 days old"),
            _video("b", "20260101", 100, "10 days old"),
            _video("c", "20251202", 100, "40 days old"),
        ]  # gaps 30, 5 -> uneven
        derived = compute(CHANNEL, videos, now=NOW)
        self.assertGreater(derived.channel["upload_interval_cv"], 0.0)

    def test_cv_needs_at_least_two_gaps(self) -> None:
        # Two videos -> one gap -> CV undefined; median/max still defined.
        two = VIDEOS[:2]
        derived = compute(CHANNEL, two, now=NOW)
        self.assertIsNone(derived.channel["upload_interval_cv"])
        self.assertEqual(derived.channel["median_upload_interval_days"], 10.0)

    def test_cadence_is_none_with_a_single_dated_video(self) -> None:
        derived = compute(CHANNEL, VIDEOS[:1], now=NOW)
        self.assertIsNone(derived.channel["median_upload_interval_days"])
        self.assertIsNone(derived.channel["max_upload_interval_days"])
        self.assertIsNone(derived.channel["upload_interval_cv"])

    def test_undated_videos_drop_out_of_cadence(self) -> None:
        # The undated video is excluded; cadence is computed over the dated three.
        videos = [*VIDEOS, _video("bad", "not-a-date", 100, "No date")]
        derived = compute(CHANNEL, videos, now=NOW)
        self.assertEqual(derived.channel["median_upload_interval_days"], 10.0)


class EngineTests(unittest.TestCase):
    def test_missing_raw_data_propagates_as_none_and_leaves_the_series(self) -> None:
        videos = [*VIDEOS, _video("v4", "20260101", None, "Views hidden")]
        derived = compute(CHANNEL, videos, now=NOW)
        self.assertIsNone(derived.videos["v4"]["views_per_day"])
        self.assertIsNone(derived.videos["v4"]["performance_index"])
        # v4 drops out of the series rather than poisoning the baseline.
        self.assertEqual(derived.channel["median_views_per_day"], 100.0)

    def test_only_pulls_in_transitive_dependencies(self) -> None:
        derived = compute(CHANNEL, VIDEOS, now=NOW, only=["performance_index"])
        self.assertEqual(
            set(derived.videos["v1"]),
            {"performance_index", "views_per_day", "upload_age_days"},
        )
        self.assertEqual(set(derived.channel), {"median_views_per_day"})
        self.assertAlmostEqual(derived.videos["v3"]["performance_index"], 2.0)

    def test_requesting_an_unknown_metric_is_an_error(self) -> None:
        with self.assertRaises(MetricError):
            compute(CHANNEL, VIDEOS, now=NOW, only=["clickbait_score"])

    def test_circular_dependencies_are_detected(self) -> None:
        cyclic = {
            "a": Metric("a", "video", "ratio", ("b",), lambda b: b),
            "b": Metric("b", "video", "ratio", ("a",), lambda a: a),
        }
        with self.assertRaisesRegex(MetricError, "circular"):
            compute(CHANNEL, VIDEOS, now=NOW, metrics=cyclic)

    def test_dependency_on_an_unknown_raw_field_is_an_error(self) -> None:
        broken = {
            "bogus": Metric("bogus", "video", "ratio", ("nope",), lambda nope: nope),
        }
        with self.assertRaisesRegex(MetricError, "nope"):
            compute(CHANNEL, VIDEOS, now=NOW, metrics=broken)

    def test_a_new_metric_composes_without_touching_the_engine(self) -> None:
        # The point of the layer: a metric built on other metrics is one function.
        extended = registry()
        extended["views_per_word"] = Metric(
            name="views_per_word",
            scope="video",
            unit="views/day/word",
            depends_on=("views_per_day", "title_word_count"),
            fn=lambda views_per_day, title_word_count: views_per_day / title_word_count,
        )
        derived = compute(CHANNEL, VIDEOS, now=NOW, metrics=extended)
        self.assertAlmostEqual(derived.videos["v1"]["views_per_word"], 100.0 / 3)


if __name__ == "__main__":
    unittest.main()
