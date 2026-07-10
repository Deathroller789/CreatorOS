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
    def test_metrics_are_discovered_without_being_imported(self) -> None:
        # Importing the package alone must populate the registry: adding a metric
        # module is additive, and nothing has to be wired up by hand.
        self.assertLessEqual(
            {
                "upload_age_days",
                "views_per_day",
                "performance_index",
                "title_length",
                "title_word_count",
                "median_views_per_day",
            },
            set(registry()),
        )

    def test_every_metric_declares_a_unit_and_a_scope(self) -> None:
        for name, m in registry().items():
            with self.subTest(metric=name):
                self.assertTrue(m.unit, f"{name} has no unit")
                self.assertIn(m.scope, ("video", "channel"))

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
