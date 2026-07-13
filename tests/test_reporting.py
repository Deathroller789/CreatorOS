"""Tests for the reporting layer (metadata + Markdown renderer)."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from creatoros.intelligence.findings import (
    CadenceFindings,
    ChannelFindings,
    ChannelRef,
    Confidence,
    CorpusGroup,
    CorpusPhrase,
    FeatureComparison,
    FeatureGroup,
    OutlierFindings,
    VideoOutlier,
)
from creatoros.reporting import (
    DESCRIPTIVE_DISCLAIMER,
    JsonRenderer,
    MarkdownRenderer,
    ReportMetadata,
    build_metadata,
)

NOW = datetime(2026, 1, 11, tzinfo=UTC)

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
MARKDOWN_GOLDEN = GOLDEN_DIR / "channel_report.md"
JSON_GOLDEN = GOLDEN_DIR / "channel_report.json"

# The installed package version leaks into report provenance. Pin it for the golden
# fixture so the committed files depend only on *rendering*, not on the environment's
# version string — the whole point of a rendering regression test.
_PINNED_VERSION = "0.0.0-test"


def _findings() -> ChannelFindings:
    """A hand-built findings fixture — reporting depends on findings, not on the DB."""
    return ChannelFindings(
        channel=ChannelRef("UC1", "Test Channel", "@test", "https://x", 1000),
        sample_size=3,
        outliers=OutlierFindings(
            baseline_views_per_day=100.0,
            baseline_iqr_low=60.0,
            baseline_iqr_high=175.0,
            baseline_basis_n=3,
            baseline_excluded_recent=0,
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
        feature_groups=(
            FeatureGroup(
                category="title",
                label="Title evidence",
                sample_size=3,
                above_n=2,
                below_n=1,
                features=(
                    FeatureComparison(
                        "title_length", "characters", 5.0, 12.0, -7.0, -0.9, 2, 1
                    ),
                ),
                confidence=Confidence("low", "n=3: too small."),
            ),
        ),
        corpus_groups=(
            CorpusGroup(
                category="corpus:title",
                label="Recurring title phrases",
                basis_n=3,
                sample_size=3,
                phrases=(
                    CorpusPhrase("big win", 2, 2, 2 / 3, None, None),
                    CorpusPhrase("title", 1, 2, 2 / 3, None, None),
                ),
                confidence=Confidence("low", "n=3: too small."),
                coverage_note=None,
            ),
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


def _golden_metadata() -> ReportMetadata:
    """Metadata for the fixture with the environment-dependent version pinned, so the
    golden files change only when rendering changes."""
    meta = build_metadata(_findings(), now=NOW)
    return replace(
        meta, creatoros_version=_PINNED_VERSION, metric_engine_version=_PINNED_VERSION
    )


def _render_markdown_golden() -> str:
    return MarkdownRenderer().render(_findings(), _golden_metadata())


def _render_json_golden() -> str:
    return JsonRenderer().render(_findings(), _golden_metadata())


class MetadataTests(unittest.TestCase):
    def test_metadata_carries_provenance(self) -> None:
        m = build_metadata(_findings(), now=NOW)
        self.assertTrue(m.creatoros_version)
        self.assertEqual(m.metric_engine_version, m.creatoros_version)
        self.assertEqual(m.report_format_version, 2)
        self.assertEqual(m.generated_at, "2026-01-11T00:00:00+00:00")
        self.assertEqual(m.channel_id, "UC1")
        self.assertEqual(m.sample_size, 3)

    def test_confidence_summary_is_the_most_conservative_level(self) -> None:
        # Primary groups are low/moderate/low -> the report summary is the worst: low.
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
        # Performance (ranked videos), the title comparison, corpus phrases, cadence.
        self.assertIn("100 views/day", self.out)  # baseline
        for v in self.findings.outliers.ranking:
            self.assertIn(f"{v.performance_index:.2f}x", self.out)
        self.assertIn("title_length", self.out)
        self.assertIn("big win", self.out)  # corpus phrase
        self.assertIn("regular", self.out)

    def test_escapes_pipes_in_titles(self) -> None:
        # "Big | win" must not break the table.
        self.assertIn("Big \\| win", self.out)

    def test_render_is_deterministic(self) -> None:
        again = MarkdownRenderer().render(self.findings, self.metadata)
        self.assertEqual(self.out, again)

    def test_confidence_stated_once_not_per_section(self) -> None:
        # #44: "evidence quality" (the header confidence phrasing) appears exactly once,
        # instead of being repeated in every section.
        self.assertEqual(self.out.count("evidence quality"), 1)

    def test_header_confidence_carries_its_reason(self) -> None:
        # #44: the single confidence line explains itself, not just a bare label.
        self.assertIn("too small", self.out)  # the fixture's low-confidence reason

    def test_section_confidence_shown_only_when_it_differs(self) -> None:
        # Fixture cadence is 'moderate' vs overall 'low' -> the divergence is surfaced.
        self.assertIn("· confidence: moderate", self.out)
        self.assertNotIn("· confidence: low", self.out)

    def test_recent_column_hidden_when_no_video_is_recent(self) -> None:
        # #43: fixture videos are all non-recent, so the dead column is dropped.
        self.assertNotIn("Recent", self.out)

    def test_recent_column_shown_when_a_video_is_recent(self) -> None:
        f = _findings()
        ranking = (
            replace(f.outliers.ranking[0], is_recent=True),
            *f.outliers.ranking[1:],
        )
        f2 = replace(f, outliers=replace(f.outliers, ranking=ranking))
        out = MarkdownRenderer().render(f2, build_metadata(f2, now=NOW))
        self.assertIn("Recent", out)
        self.assertIn("yes", out)

    def test_baseline_rounded_to_significant_figures(self) -> None:
        # #48: a six-figure baseline from a sample is false precision; show magnitude.
        f = _findings()
        f2 = replace(f, outliers=replace(f.outliers, baseline_views_per_day=143_747.0))
        out = MarkdownRenderer().render(f2, build_metadata(f2, now=NOW))
        self.assertIn("144,000", out)
        self.assertNotIn("143,747", out)

    def test_small_sample_baseline_carries_a_caveat(self) -> None:
        # #48: fixture basis n=3 (< 10) -> the baseline is flagged as volatile.
        self.assertIn("Small sample", self.out)

    def test_adequate_sample_has_no_small_sample_caveat(self) -> None:
        f = _findings()
        f2 = replace(f, outliers=replace(f.outliers, baseline_basis_n=50))
        out = MarkdownRenderer().render(f2, build_metadata(f2, now=NOW))
        self.assertNotIn("Small sample", out)

    def test_corpus_split_columns_shown_when_present(self) -> None:
        # When the above/below split is available, the corpus table carries it.
        f = _findings()
        split_phrase = replace(
            f.corpus_groups[0].phrases[0], above_count=2, below_count=0
        )
        group = replace(f.corpus_groups[0], phrases=(split_phrase,))
        f2 = replace(f, corpus_groups=(group,))
        out = MarkdownRenderer().render(f2, build_metadata(f2, now=NOW))
        self.assertIn("Above baseline", out)
        self.assertIn("Below baseline", out)


class JsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.findings = _findings()
        self.metadata = build_metadata(self.findings, now=NOW)
        self.out = JsonRenderer().render(self.findings, self.metadata)

    def test_output_is_valid_json_with_the_expected_shape(self) -> None:
        doc = json.loads(self.out)
        self.assertEqual(set(doc), {"notice", "metadata", "findings"})
        self.assertEqual(doc["notice"], DESCRIPTIVE_DISCLAIMER)
        self.assertEqual(doc["metadata"]["channel_id"], "UC1")
        self.assertEqual(doc["findings"]["sample_size"], 3)

    def test_carries_every_finding_losslessly(self) -> None:
        doc = json.loads(self.out)
        ranking = doc["findings"]["outliers"]["ranking"]
        self.assertEqual([o["video_id"] for o in ranking], ["v3", "v1", "v2"])
        self.assertEqual(ranking[0]["performance_index"], 2.0)
        self.assertEqual(doc["findings"]["outliers"]["baseline_views_per_day"], 100.0)
        self.assertEqual(doc["findings"]["cadence"]["regularity"], "regular")
        feature = doc["findings"]["feature_groups"][0]["features"][0]
        self.assertEqual(feature["metric"], "title_length")
        phrase = doc["findings"]["corpus_groups"][0]["phrases"][0]
        self.assertEqual(phrase["text"], "big win")

    def test_render_is_deterministic(self) -> None:
        again = JsonRenderer().render(self.findings, self.metadata)
        self.assertEqual(self.out, again)


class GoldenRegressionTests(unittest.TestCase):
    """Deterministic renderers vs committed reference bytes.

    The same frozen, synthetic findings must render to byte-for-byte identical Markdown
    and JSON. A mismatch means rendering changed; if that change is intended, regenerate
    the golden files with::

        uv run python tests/test_reporting.py --update-golden

    Production data is never used here — the fixture is hand-built.
    """

    def test_markdown_matches_golden(self) -> None:
        self.assertEqual(
            _render_markdown_golden().encode("utf-8"),
            MARKDOWN_GOLDEN.read_bytes(),
            "Markdown rendering changed; regenerate the golden file if intended.",
        )

    def test_json_matches_golden(self) -> None:
        self.assertEqual(
            _render_json_golden().encode("utf-8"),
            JSON_GOLDEN.read_bytes(),
            "JSON rendering changed; regenerate the golden file if intended.",
        )

    def test_golden_rendering_is_deterministic(self) -> None:
        self.assertEqual(_render_markdown_golden(), _render_markdown_golden())
        self.assertEqual(_render_json_golden(), _render_json_golden())

    def test_both_formats_carry_the_same_information(self) -> None:
        # JSON is the canonical, lossless form; Markdown is presentation. Every fact the
        # JSON records must also appear in the Markdown — only the shape differs. (JSON
        # identifies videos by id, Markdown by title/url, so match on title + index.)
        md = _render_markdown_golden()
        doc = json.loads(_render_json_golden())
        self.assertIn(doc["notice"], md)
        self.assertIn(doc["metadata"]["creatoros_version"], md)
        self.assertIn(doc["metadata"]["channel_id"], md)
        findings = doc["findings"]
        for video in findings["outliers"]["ranking"]:
            self.assertIn(f"{video['performance_index']:.2f}x", md)
            self.assertIn(video["title"].replace("|", "\\|"), md)
        self.assertIn(findings["feature_groups"][0]["features"][0]["metric"], md)
        self.assertIn(findings["corpus_groups"][0]["phrases"][0]["text"], md)
        self.assertIn(findings["cadence"]["regularity"], md)


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


def _write_golden_files() -> None:
    """Regenerate the committed golden files. LF newline is forced so the files stay
    byte-stable across platforms regardless of ``core.autocrlf`` (see issue #18)."""
    GOLDEN_DIR.mkdir(exist_ok=True)
    MARKDOWN_GOLDEN.write_text(
        _render_markdown_golden(), encoding="utf-8", newline="\n"
    )
    JSON_GOLDEN.write_text(_render_json_golden(), encoding="utf-8", newline="\n")
    print(f"Wrote {MARKDOWN_GOLDEN}\nWrote {JSON_GOLDEN}")


if __name__ == "__main__":
    if "--update-golden" in sys.argv:
        _write_golden_files()
    else:
        unittest.main()
