"""Channel-scope derived metrics. A channel metric sees a video metric as a series."""

from __future__ import annotations

import statistics

from creatoros.metrics.engine import metric

# Below this many settled videos, excluding fresh uploads leaves too little to form a
# baseline from, so we use the full sample rather than a two-video median (issue #48).
# Above it, the baseline is the settled videos only — the representative set.
_MIN_SETTLED_FOR_BASELINE = 5


def _baseline_basis(
    settled_views_per_day: list[float], views_per_day: list[float]
) -> list[float]:
    """The view-rate series the baseline is computed over.

    Settled videos (launch spike passed) when there are enough of them; otherwise the
    whole sample, since excluding recent uploads from a tiny channel would leave almost
    nothing (issue #48). Deterministic: the choice depends only on the counts.
    """
    if len(settled_views_per_day) >= _MIN_SETTLED_FOR_BASELINE:
        return settled_views_per_day
    return views_per_day


@metric(
    scope="channel",
    unit="views/day",
    depends_on=("settled_views_per_day", "views_per_day"),
)
def baseline_views_per_day(
    settled_views_per_day: list[float], views_per_day: list[float]
) -> float | None:
    """The channel's representative view rate: the median of settled videos.

    Median, not mean, so one viral video cannot move it; settled, not most-recent, so a
    launch spike cannot inflate it (issue #48). ``None`` when the sample is empty.
    """
    basis = _baseline_basis(settled_views_per_day, views_per_day)
    if not basis:
        return None
    return statistics.median(basis)


@metric(
    scope="channel",
    unit="count",
    depends_on=("settled_views_per_day", "views_per_day"),
)
def baseline_basis_count(
    settled_views_per_day: list[float], views_per_day: list[float]
) -> int:
    """How many videos the baseline was actually computed over (its real sample)."""
    return len(_baseline_basis(settled_views_per_day, views_per_day))


@metric(
    scope="channel",
    unit="views/day",
    depends_on=("settled_views_per_day", "views_per_day"),
)
def baseline_iqr_low(
    settled_views_per_day: list[float], views_per_day: list[float]
) -> float | None:
    """The 25th percentile of the baseline basis — the low edge of typical performance.

    Reported beside the median so the baseline reads as a spread, not a false-precise
    point (issue #48). ``None`` with fewer than two videos (quartile undefined).
    """
    basis = _baseline_basis(settled_views_per_day, views_per_day)
    if len(basis) < 2:
        return None
    return statistics.quantiles(basis, n=4)[0]


@metric(
    scope="channel",
    unit="views/day",
    depends_on=("settled_views_per_day", "views_per_day"),
)
def baseline_iqr_high(
    settled_views_per_day: list[float], views_per_day: list[float]
) -> float | None:
    """The 75th percentile of the basis — the high edge of typical performance."""
    basis = _baseline_basis(settled_views_per_day, views_per_day)
    if len(basis) < 2:
        return None
    return statistics.quantiles(basis, n=4)[2]


def _upload_intervals(upload_age_days: list[float]) -> list[float]:
    """Days between consecutive uploads, from the age series (oldest to newest).

    Sorting ages descending puts the oldest upload first; each consecutive difference is
    the gap to the next upload. Videos with an unusable date are dropped upstream, so a
    missing middle upload merges two real gaps into one — a known, honest limitation at
    this sample size (see `docs/modules/002-channel-intelligence.md`, Q3).
    """
    ages = sorted(upload_age_days, reverse=True)
    return [older - newer for older, newer in zip(ages, ages[1:], strict=False)]


@metric(scope="channel", unit="days", depends_on=("upload_age_days",))
def median_upload_interval_days(upload_age_days: list[float]) -> float | None:
    """Typical gap between uploads. ``None`` with fewer than two dated videos."""
    intervals = _upload_intervals(upload_age_days)
    if not intervals:
        return None
    return statistics.median(intervals)


@metric(scope="channel", unit="days", depends_on=("upload_age_days",))
def max_upload_interval_days(upload_age_days: list[float]) -> float | None:
    """Longest gap between uploads — the channel's biggest dry spell in the sample."""
    intervals = _upload_intervals(upload_age_days)
    if not intervals:
        return None
    return max(intervals)


@metric(scope="channel", unit="ratio", depends_on=("upload_age_days",))
def upload_interval_cv(upload_age_days: list[float]) -> float | None:
    """Cadence consistency: coefficient of variation of the gaps.

    ``0`` is perfectly regular; higher is more erratic. Dimensionless (stdev / mean), so
    it describes regularity independent of posting speed. ``None`` with fewer than two
    gaps (needs three dated videos), or if the mean gap is zero.
    """
    intervals = _upload_intervals(upload_age_days)
    if len(intervals) < 2:
        return None
    mean = statistics.fmean(intervals)
    if mean == 0:
        return None
    return statistics.stdev(intervals) / mean
