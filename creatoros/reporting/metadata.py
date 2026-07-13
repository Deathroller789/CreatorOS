"""Report metadata — provenance for a rendered report, independent of output format.

Assembled from findings once, then handed to any renderer, so every format carries the
same provenance. Pure: no metric computation, no analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version

from creatoros.intelligence.findings import ChannelFindings

# Bump when the *structure* of a report changes (fields added/removed/renamed), so a
# stored report reads against the right expectations. v2: evidence-group findings —
# discovered feature groups and corpus (recurring-phrase) groups; baseline gained its
# settled basis and spread (ADR-008, additive schema evolution).
REPORT_FORMAT_VERSION = 2

# Stated in every report, in every format. Confidence here is a statement about evidence
# quality (sample size) — never a probability of a future outcome.
DESCRIPTIVE_DISCLAIMER = "This report is descriptive, not predictive."

_LEVEL_ORDER = {"low": 0, "moderate": 1, "reasonable": 2}


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    """Provenance stamped on every report, whatever the renderer."""

    creatoros_version: str
    metric_engine_version: str
    report_format_version: int
    generated_at: str  # ISO 8601
    channel_id: str
    channel_title: str | None
    sample_size: int
    # The most conservative evidence-quality level across the report's finding groups.
    confidence_summary: str


def _package_version() -> str:
    try:
        return version("creator-os")
    except PackageNotFoundError:
        return "0+unknown"


def _overall_confidence(findings: ChannelFindings) -> str:
    """The most conservative confidence level across the report's primary groups.

    Performance, cadence, and the scalar feature groups all rest on the full sample, so
    they set the report's headline confidence. Corpus groups carry their own (often
    thinner, transcript-limited) confidence inline and are excluded here, so a channel
    with rich metadata but few transcripts is not mislabeled low overall.
    """
    levels = [
        findings.outliers.confidence.level,
        findings.cadence.confidence.level,
        *(g.confidence.level for g in findings.feature_groups),
    ]
    return min(levels, key=lambda level: _LEVEL_ORDER.get(level, 0))


def build_metadata(
    findings: ChannelFindings, now: datetime | None = None
) -> ReportMetadata:
    """Assemble report provenance from findings. ``now`` is injectable for tests."""
    package = _package_version()
    generated = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    return ReportMetadata(
        creatoros_version=package,
        # The engine ships inside the CreatorOS package and is not versioned on its own
        # yet; the two coincide until it is (debt). Only this source changes then.
        metric_engine_version=package,
        report_format_version=REPORT_FORMAT_VERSION,
        generated_at=generated,
        channel_id=findings.channel.channel_id,
        channel_title=findings.channel.title,
        sample_size=findings.sample_size,
        confidence_summary=f"{_overall_confidence(findings)} (evidence quality)",
    )
