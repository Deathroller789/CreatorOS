"""Channel-scope derived metrics. A channel metric sees a video metric as a series."""

from __future__ import annotations

import statistics

from creatoros.metrics.engine import metric


@metric(scope="channel", unit="views/day", depends_on=("views_per_day",))
def median_views_per_day(views_per_day: list[float]) -> float | None:
    """The channel's baseline. Median, not mean: one viral video must not move it."""
    if not views_per_day:
        return None
    return statistics.median(views_per_day)


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
