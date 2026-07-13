"""Canonical findings — the contract between Intelligence and Reporting.

Plain, immutable data. No behavior, no presentation, no knowledge of any output format
or of SQLite. A renderer consumes these; intelligence produces them. Every value here is
either a **derived** metric or a raw identifier (title, url) kept for reference only,
never a raw fact used to reach a conclusion.

The shape is *evidence-group oriented* (RFC-002): performance, cadence, a feature group
per scalar family (title, ...), and one corpus group per recurring-phrase family (title
phrases, openings, endings, spoken phrases). The intelligence layer fills these by
discovering families from the registry, so a new family is new findings, no change to
this contract's consumers.

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
    """Q1 — videos ranked by age-normalized performance against the channel baseline.

    The baseline is the median of *settled* videos (launch spike passed), reported with
    its interquartile spread and the size of the set it covers, so it reads as a
    distribution rather than a false-precise point (issue #48).
    """

    baseline_views_per_day: float | None
    baseline_iqr_low: float | None
    baseline_iqr_high: float | None
    baseline_basis_n: int  # videos the baseline was computed over
    baseline_excluded_recent: int  # fresh videos excluded from the baseline
    sample_size: int
    ranking: tuple[VideoOutlier, ...]  # sorted by performance_index, descending
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class FeatureComparison:
    """One scalar metric contrasted between above- and below-baseline videos."""

    metric: str
    unit: str
    above_mean: float
    below_mean: float
    difference: float
    effect_size: float | None  # Cohen's d; None if a group is too small to estimate
    above_n: int
    below_n: int


@dataclass(frozen=True, slots=True)
class FeatureGroup:
    """A family of scalar evidence (e.g. "title") compared across the baseline split.

    ``category`` is the registry family the metrics came from; ``label`` is its display
    name. Discovered from the registry, so a new metric in the family joins its group
    with no change here (ADR-006).
    """

    category: str
    label: str
    sample_size: int
    above_n: int
    below_n: int
    features: tuple[FeatureComparison, ...]
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class CorpusPhrase:
    """One recurring phrase and how widely (and where) it recurs.

    ``document_count`` is how many videos' text contains the phrase: recurrence across
    observations, not term frequency (RFC-002: repetition is what makes an observation
    stronger evidence). ``above_count``/``below_count`` split that recurrence by
    performance group when both groups are big enough to compare, else ``None`` — the
    deterministic seam of the "why did this work" question (issue #47).
    """

    text: str
    size: int  # n-gram length (1, 2, 3)
    document_count: int
    document_ratio: float
    above_count: int | None
    below_count: int | None


@dataclass(frozen=True, slots=True)
class CorpusGroup:
    """A recurring-phrase evidence family (title phrases, openings, endings, spoken).

    Corpus evidence (RFC-002): deterministic, descriptive. ``basis_n`` is the number of
    videos that contributed text; ``coverage_note`` states any shortfall (e.g. missing
    transcripts) plainly rather than hiding it (ADR-009).
    """

    category: str
    label: str
    basis_n: int
    sample_size: int
    phrases: tuple[CorpusPhrase, ...]
    confidence: Confidence
    coverage_note: str | None


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
    """The complete analysis of one channel: the contract handed to a renderer.

    ``feature_groups`` and ``corpus_groups`` are ordered as the report should read them;
    both are discovered from the registry, not hard-coded, so growing the evidence base
    grows the report without touching this contract's consumers.
    """

    channel: ChannelRef
    sample_size: int
    outliers: OutlierFindings
    feature_groups: tuple[FeatureGroup, ...]
    corpus_groups: tuple[CorpusGroup, ...]
    cadence: CadenceFindings
