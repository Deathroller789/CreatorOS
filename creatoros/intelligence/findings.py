"""Canonical findings — the contract between Intelligence and Reporting.

Plain, immutable data. No behavior, no presentation, no knowledge of any output format
or of SQLite. A renderer consumes these; intelligence produces them. Every value here is
either a **derived** metric or a raw identifier (title, url) kept for reference only,
never a raw fact used to reach a conclusion.

Design rules these types encode (docs/modules/002-channel-intelligence.md):
- Every finding group carries a ``sample_size`` and a ``Confidence``. Nothing hides n.
- Outliers are a **ranking**, not a threshold — the ranking is the finding.
- Descriptive only: numbers and comparisons, never a prediction or a recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Confidence:
    """A plain-language qualifier tied to the sample. Never higher than 'reasonable' —
    this layer is descriptive, not predictive."""

    level: str  # "low" | "moderate" | "reasonable"
    reason: str


@dataclass(frozen=True, slots=True)
class ChannelRef:
    """Identity of the analyzed channel. Reference only — not used in any conclusion."""

    channel_id: str
    title: str | None
    handle: str | None
    url: str | None
    subscriber_count: int | None


@dataclass(frozen=True, slots=True)
class VideoOutlier:
    """One video's standing against the channel baseline, entirely in derived terms.

    ``views_per_day`` is the age-normalized 'actual'; the baseline it compares against
    lives on :class:`OutlierFindings`. ``title``/``url`` are for reference only.
    """

    video_id: str
    title: str | None
    url: str | None
    upload_age_days: float
    views_per_day: float
    performance_index: float
    difference_views_per_day: float
    is_recent: bool  # very fresh: the rate is a spike that may not hold


@dataclass(frozen=True, slots=True)
class OutlierFindings:
    """Q1 — videos ranked by age-normalized performance against the channel median."""

    baseline_views_per_day: float | None
    sample_size: int
    ranking: tuple[VideoOutlier, ...]  # sorted by performance_index, descending
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class TitleFeatureComparison:
    """One title metric contrasted between above- and below-baseline videos."""

    metric: str
    unit: str
    above_mean: float
    below_mean: float
    difference: float
    effect_size: float | None  # Cohen's d; None if a group is too small to estimate
    above_n: int
    below_n: int


@dataclass(frozen=True, slots=True)
class TitleFindings:
    """Q2 — how title metrics differ between above- and below-baseline videos."""

    sample_size: int
    above_n: int
    below_n: int
    features: tuple[TitleFeatureComparison, ...]
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class CadenceFindings:
    """Q3 — how regularly the channel publishes, across the sampled window."""

    sample_size: int  # videos with a usable upload date
    median_interval_days: float | None
    max_interval_days: float | None
    consistency_cv: float | None
    regularity: str  # "regular" | "somewhat irregular" | "erratic" | "unknown"
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class ChannelFindings:
    """The complete V1 analysis of one channel: the contract handed to a renderer."""

    channel: ChannelRef
    sample_size: int
    outliers: OutlierFindings
    titles: TitleFindings
    cadence: CadenceFindings
