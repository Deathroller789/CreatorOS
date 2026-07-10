"""Video-scope derived metrics. Pure functions; the engine supplies every argument."""

from __future__ import annotations

from datetime import UTC, datetime

from creatoros.metrics.engine import metric

# A video published minutes ago has an age near zero, and views/day would explode toward
# infinity. Floor the denominator at one day: a brand-new video is reported at its raw
# view count, never as a spurious outlier.
_MIN_AGE_DAYS = 1.0


@metric(scope="video", unit="days", depends_on=("upload_date", "now"))
def upload_age_days(upload_date: str, now: datetime) -> float | None:
    """Days since the video was published, or ``None`` if the date is unusable."""
    try:
        uploaded = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None
    return max((now - uploaded).total_seconds() / 86_400.0, 0.0)


@metric(scope="video", unit="views/day", depends_on=("view_count", "upload_age_days"))
def views_per_day(view_count: int, upload_age_days: float) -> float:
    """Age-normalized reach: raw views cannot be compared across upload dates."""
    return view_count / max(upload_age_days, _MIN_AGE_DAYS)


@metric(
    scope="video",
    unit="ratio",
    depends_on=("views_per_day", "median_views_per_day"),
)
def performance_index(
    views_per_day: float, median_views_per_day: float
) -> float | None:
    """Views/day against the channel baseline: ``2.7`` means 2.7x baseline."""
    if not median_views_per_day:
        return None
    return views_per_day / median_views_per_day


@metric(scope="video", unit="characters", depends_on=("title",))
def title_length(title: str) -> int:
    """Character count of the video title."""
    return len(title)


@metric(scope="video", unit="words", depends_on=("title",))
def title_word_count(title: str) -> int:
    """Whitespace-delimited word count of the video title."""
    return len(title.split())
