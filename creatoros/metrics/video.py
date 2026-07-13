"""Video-scope derived metrics. Pure functions; the engine supplies every argument."""

from __future__ import annotations

from datetime import UTC, datetime

from creatoros.metrics.engine import metric
from creatoros.metrics.text import tokenize

# A video published minutes ago has an age near zero, and views/day would explode toward
# infinity. Floor the denominator at one day: a brand-new video is reported at its raw
# view count, never as a spurious outlier.
_MIN_AGE_DAYS = 1.0

# Within this window of upload the view rate is still inflated by the launch spike, so a
# fresh video is excluded from the *baseline* (issue #48): a baseline built from videos
# that have not settled reads high and shifts with `--limit`. The video is never dropped
# from the ranking — only from the yardstick it is measured against.
_SETTLED_AGE_DAYS = 7.0

# How many leading / trailing transcript tokens count as the "opening" and "ending": the
# region where recurring hooks and calls-to-action live (narrative signals, RFC-002).
_OPENING_TOKENS = 40
_CLOSING_TOKENS = 40


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
    unit="views/day",
    depends_on=("views_per_day", "upload_age_days"),
)
def settled_views_per_day(views_per_day: float, upload_age_days: float) -> float | None:
    """``views_per_day`` once the launch spike has passed, else ``None``.

    The channel baseline is the median of this series (see ``channel.py``), so a
    just-published video contributes its settled peers' rate, not its own inflated one
    (issue #48). ``None`` drops the video from the baseline while leaving it in the
    ranking, where its recency is flagged instead.
    """
    return views_per_day if upload_age_days >= _SETTLED_AGE_DAYS else None


@metric(
    scope="video",
    unit="ratio",
    depends_on=("views_per_day", "baseline_views_per_day"),
)
def performance_index(
    views_per_day: float, baseline_views_per_day: float
) -> float | None:
    """Views/day against the channel baseline: ``2.7`` means 2.7x baseline."""
    if not baseline_views_per_day:
        return None
    return views_per_day / baseline_views_per_day


# --- Title structure evidence (issues #46, #48) ------------------------------------
# Each is a deterministic per-video scalar in the "title" family, so the intelligence
# layer picks them up by category with no code change (ADR-006). Booleans are 0/1 so a
# group mean reads as a proportion ("60% of titles pose a question") — the
# recurring-structure evidence a later synthesis layer can reason over. No LLM.


@metric(scope="video", unit="characters", depends_on=("title",), category="title")
def title_length(title: str) -> int:
    """Character count of the video title."""
    return len(title)


@metric(scope="video", unit="words", depends_on=("title",), category="title")
def title_word_count(title: str) -> int:
    """Whitespace-delimited word count of the video title."""
    return len(title.split())


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


# --- Corpus token evidence (issues #45, #46) ---------------------------------------
# These return the per-video *tokens* the intelligence layer aggregates into recurring
# phrases (corpus evidence, RFC-002). The category ("corpus:...") both marks them as
# corpus families and tells the analysis how to group them — adding a corpus family is
# one decorated function, no analysis change (ADR-006). A video missing the source text
# returns ``None`` and drops from the corpus (ADR-009: quiet absence, never invented).


@metric(scope="video", unit="tokens", depends_on=("title",), category="corpus:title")
def title_tokens(title: str) -> list[str] | None:
    """Normalised tokens of the title, for recurring title-phrase evidence."""
    tokens = tokenize(title)
    return tokens or None


@metric(
    scope="video",
    unit="tokens",
    depends_on=("transcript_text",),
    category="corpus:transcript",
)
def transcript_tokens(transcript_text: str | None) -> list[str] | None:
    """All normalised transcript tokens, for recurring in-video phrase evidence."""
    tokens = tokenize(transcript_text)
    return tokens or None


@metric(
    scope="video",
    unit="tokens",
    depends_on=("transcript_text",),
    category="corpus:opening",
)
def transcript_opening_tokens(transcript_text: str | None) -> list[str] | None:
    """The first tokens of the transcript — where a recurring hook would live."""
    tokens = tokenize(transcript_text)
    return tokens[:_OPENING_TOKENS] or None


@metric(
    scope="video",
    unit="tokens",
    depends_on=("transcript_text",),
    category="corpus:closing",
)
def transcript_closing_tokens(transcript_text: str | None) -> list[str] | None:
    """The last tokens of the transcript — where a recurring sign-off would live."""
    tokens = tokenize(transcript_text)
    return tokens[-_CLOSING_TOKENS:] or None
