"""Tests for the reporting layer (metadata + Markdown renderer)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path

from creatoros.intelligence.findings import (
    CadenceFindings,
    ChannelFindings,
    ChannelRef,
    Confidence,
    OutlierFindings,
    TitleFeatureComparison,
    TitleFindings,
    VideoOutlier,
)
from creatoros.reporting import (
    DESCRIPTIVE_DISCLAIMER,
    MarkdownRenderer,
    build_metadata,
)

NOW = datetime(2026, 1, 11, tzinfo=UTC)


def _findings() -> ChannelFindings:
    """A hand-built findings fixture — reporting depends on findings, not on the DB."""
    return ChannelFindings(
        channel=ChannelRef("UC1", "Test Channel", "@test", "https://x", 1000),
        sample_size=3,
        outliers=OutlierFindings(
            baseline_views_per_day=100.0,
            sample_size=3,
            ranking=(
                VideoOutlier(
                    "v3", "Big | win", "https://y/v3", 30.0, 200.0, 2.0, 100.0, False
                ),
                VideoOutlier(
                    "v1", "Short", "https://y/v1", 10.0, 100.0, 1.0, 0.0, False
                ),
                VideoOutlier(
                    "v2", "Longer title", "https://y/v2", 20.0, 50.0, 0.5, -50.0, False
                ),
            ),
            confidence=Confidence("low", "n=3: too small."),
        ),
        titles=TitleFindings(
            sample_size=3,
            above_n=2,
            below_n=1,
            features=(
                TitleFeatureComparison(
                    "title_length", "characters", 5.0, 12.0, -7.0, -0.9, 2, 1
                ),
            ),
            confidence=Confidence("low", "n=3: too small."),
        ),
        cadence=CadenceFindings(
            sample_size=3,
            median_interval_days=10.0,
            max_interval_days=10.0,
            consistency_cv=0.0,
            regularity="regular",
            confidence=Confidence("moderate", "n=3."),
        ),
    )


class MetadataTests(unittest.TestCase):
    def test_metadata_carries_provenance(self) -> None:
        m = build_metadata(_findings(), now=NOW)
        self.assertTrue(m.creatoros_version)
        self.assertEqual(m.metric_engine_version, m.creatoros_version)
        self.assertEqual(m.report_format_version, 1)
        self.assertEqual(m.generated_at, "2026-01-11T00:00:00+00:00")
        self.assertEqual(m.channel_id, "UC1")
        self.assertEqual(m.sample_size, 3)

    def test_confidence_summary_is_the_most_conservative_level(self) -> None:
        # Groups are low/low/moderate -> the report summary is the worst: low.
        m = build_metadata(_findings(), now=NOW)
        self.assertIn("low", m.confidence_summary)
        self.assertIn("evidence quality", m.confidence_summary)


class MarkdownTests(unittest.TestCase):
    def setUp(self) -> None:
        self.findings = _findings()
        self.metadata = build_metadata(self.findings, now=NOW)
        self.out = MarkdownRenderer().render(self.findings, self.metadata)

    def test_states_it_is_descriptive_not_predictive(self) -> None:
        self.assertIn(DESCRIPTIVE_DISCLAIMER, self.out)

    def test_contains_provenance_and_confidence_as_evidence_quality(self) -> None:
        self.assertIn(self.metadata.creatoros_version, self.out)
        self.assertIn("Metric engine version", self.out)
        self.assertIn("evidence quality", self.out)

    def test_contains_every_finding(self) -> None:
        # Outliers (all ranked videos), the title comparison, and cadence all appear.
        self.assertIn("100 views/day", self.out)  # baseline
        for v in self.findings.outliers.ranking:
            self.assertIn(f"{v.performance_index:.2f}x", self.out)
        self.assertIn("title_length", self.out)
        self.assertIn("regular", self.out)

    def test_escapes_pipes_in_titles(self) -> None:
        # "Big | win" must not break the table.
        self.assertIn("Big \\| win", self.out)

    def test_render_is_deterministic(self) -> None:
        again = MarkdownRenderer().render(self.findings, self.metadata)
        self.assertEqual(self.out, again)


class BoundaryTests(unittest.TestCase):
    def test_reporting_performs_no_metric_computation_or_analysis(self) -> None:
        # The layer boundary as an executable assertion: reporting consumes findings and
        # must not reach into the metrics engine or the analysis logic.
        package = Path(__file__).resolve().parent.parent / "creatoros" / "reporting"
        forbidden = ("creatoros.metrics", "import statistics", "analyze_channel")
        for source in package.glob("*.py"):
            text = source.read_text(encoding="utf-8")
            for token in forbidden:
                with self.subTest(module=source.name, token=token):
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
