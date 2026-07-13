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


@metric(scope="video", unit="characters", depends_on=("title",), category="title")
def title_length(title: str) -> int:
    """Character count of the video title."""
    return len(title)


@metric(scope="video", unit="words", depends_on=("title",), category="title")
def title_word_count(title: str) -> int:
    """Whitespace-delimited word count of the video title."""
    return len(title.split())


# Title-structure evidence (issue #48, roadmap #19). Each is a deterministic per-video
# scalar in the "title" family, so the intelligence layer picks them up by category with
# no code change (ADR-006). Booleans are 0/1 so a group mean reads as a proportion —
# e.g. "60% of above-baseline titles pose a question" — the recurring-structure evidence
# a later synthesis layer can reason over. No LLM, no new dependency.


@metric(scope="video", unit="0/1", depends_on=("title",), category="title")
def title_has_number(title: str) -> int:
    """Whether the title contains any digit (e.g. "5 ways", "Top 10")."""
    return int(any(c.isdigit() for c in title))


@metric(scope="video", unit="0/1", depends_on=("title",), category="title")
def title_starts_with_number(title: str) -> int:
    """Whether the title opens with a digit — the listicle/countdown hook."""
    stripped = title.lstrip()
    return int(bool(stripped) and stripped[0].isdigit())


@metric(scope="video", unit="0/1", depends_on=("title",), category="title")
def title_has_question(title: str) -> int:
    """Whether the title poses a question (contains '?')."""
    return int("?" in title)


@metric(scope="video", unit="0/1", depends_on=("title",), category="title")
def title_has_colon(title: str) -> int:
    """Whether the title uses a colon — the "Topic: subtitle" packaging structure."""
    return int(":" in title)


@metric(scope="video", unit="0/1", depends_on=("title",), category="title")
def title_has_brackets(title: str) -> int:
    """Whether the title uses brackets or parentheses (e.g. "[Vol. 3]", "(2026)")."""
    return int(any(c in title for c in "[]()"))


@metric(scope="video", unit="ratio", depends_on=("title",), category="title")
def title_caps_ratio(title: str) -> float | None:
    """Share of alphabetic characters that are uppercase — a proxy for SHOUTING.

    ``None`` when the title has no letters (e.g. only emoji/numbers), so it drops from
    the series rather than counting as zero.
    """
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return None
    return sum(c.isupper() for c in letters) / len(letters)
