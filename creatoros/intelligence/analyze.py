"""Channel Intelligence V1: answer Q1/Q2/Q3 and return canonical findings.

Layer discipline (docs/modules/002-channel-intelligence.md): this module sits above the
metrics engine and consumes only **derived** metrics for its conclusions. It loads raw
rows from SQLite solely to feed the engine (ADR-006); it never does arithmetic on a raw
field, and it never produces any output format — that is the reporting layer's job. It
returns a ``ChannelFindings`` and nothing else.

Scope: outlier detection (Q1), title characteristics (Q2), cadence (Q3). No topics, no
LLM, no predictions.
"""

from __future__ import annotations

import sqlite3
import statistics
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
from creatoros.metrics import compute, registry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / "database" / "creatoros.db"

# Below this age, views/day is a spike off a tiny denominator and may not hold. Flagged,
# never dropped — the reader decides.
RECENT_DAYS = 2.0

# The title metrics compared for Q2. Explicit until metrics carry a `category` field
# (roadmap #19); this then becomes a registry filter (category == "title") and new title
# metrics need no change here — the design goal from ADR-006.
TITLE_FEATURES = ("title_length", "title_word_count")


class IntelligenceError(Exception):
    """Raised when a channel cannot be analyzed (not ingested, empty, etc.)."""


def _confidence(n: int) -> Confidence:
    """Map a sample size to an honest, sample-bound qualifier. Never 'high'."""
    if n < 10:
        return Confidence(
            "low", f"n={n}: too small to separate signal from noise; suggestive only."
        )
    if n < 30:
        return Confidence("moderate", f"n={n}: suggestive, not conclusive.")
    return Confidence(
        "reasonable", f"n={n}: a usable sample, still descriptive not predictive."
    )


def _cohens_d(above: list[float], below: list[float]) -> float | None:
    """Standardized mean difference between two groups; None if too few to estimate."""
    if len(above) < 2 or len(below) < 2:
        return None
    n1, n2 = len(above), len(below)
    pooled_var = (
        (n1 - 1) * statistics.variance(above) + (n2 - 1) * statistics.variance(below)
    ) / (n1 + n2 - 2)
    if pooled_var == 0:
        return None
    return (statistics.fmean(above) - statistics.fmean(below)) / pooled_var**0.5


def _regularity(cv: float | None) -> str:
    """Describe cadence consistency from the coefficient of variation of upload gaps."""
    if cv is None:
        return "unknown"
    if cv < 0.5:
        return "regular"
    if cv < 1.0:
        return "somewhat irregular"
    return "erratic"


def _load_channel(channel: str, db_path: Path) -> tuple[dict, list[dict]]:
    """Load the raw channel row and its videos. The module's single raw-I/O boundary."""
    if not db_path.exists():
        raise IntelligenceError(f"no database at {db_path}; ingest a channel first")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM channels WHERE channel_id = ? OR handle = ? LIMIT 1",
            (channel, channel),
        ).fetchone()
        if row is None:
            raise IntelligenceError(f"channel {channel!r} not found; ingest it first")
        raw_channel = dict(row)
        videos = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM videos WHERE channel_id = ?",
                (raw_channel["channel_id"],),
            )
        ]
    finally:
        conn.close()
    if not videos:
        raise IntelligenceError(f"channel {channel!r} has no stored videos")
    return raw_channel, videos


def _analyze_outliers(videos: list[dict], derived) -> OutlierFindings:
    baseline = derived.channel.get("median_views_per_day")
    ranking: list[VideoOutlier] = []
    if baseline is not None:
        for v in videos:
            d = derived.videos[v["video_id"]]
            index = d.get("performance_index")
            rate = d.get("views_per_day")
            age = d.get("upload_age_days")
            if index is None or rate is None or age is None:
                continue
            ranking.append(
                VideoOutlier(
                    video_id=v["video_id"],
                    title=v.get("title"),
                    url=v.get("url"),
                    upload_age_days=age,
                    views_per_day=rate,
                    performance_index=index,
                    difference_views_per_day=rate - baseline,
                    is_recent=age < RECENT_DAYS,
                )
            )
    ranking.sort(key=lambda o: o.performance_index, reverse=True)
    return OutlierFindings(
        baseline_views_per_day=baseline,
        sample_size=len(ranking),
        ranking=tuple(ranking),
        confidence=_confidence(len(ranking)),
    )


def _feature_values(derived, video_ids: list[str], name: str) -> list[float]:
    """Non-null values of a derived metric across a group of videos."""
    return [
        derived.videos[i][name]
        for i in video_ids
        if derived.videos[i][name] is not None
    ]


def _analyze_titles(videos: list[dict], derived) -> TitleFindings:
    above: list[str] = []
    below: list[str] = []
    for v in videos:
        index = derived.videos[v["video_id"]].get("performance_index")
        if index is None:
            continue
        (above if index >= 1.0 else below).append(v["video_id"])

    units = {name: m.unit for name, m in registry().items()}
    features: list[TitleFeatureComparison] = []
    if above and below:
        for name in TITLE_FEATURES:
            a = _feature_values(derived, above, name)
            b = _feature_values(derived, below, name)
            if not a or not b:
                continue
            above_mean = statistics.fmean(a)
            below_mean = statistics.fmean(b)
            features.append(
                TitleFeatureComparison(
                    metric=name,
                    unit=units.get(name, ""),
                    above_mean=above_mean,
                    below_mean=below_mean,
                    difference=above_mean - below_mean,
                    effect_size=_cohens_d(a, b),
                    above_n=len(a),
                    below_n=len(b),
                )
            )
    return TitleFindings(
        sample_size=len(above) + len(below),
        above_n=len(above),
        below_n=len(below),
        features=tuple(features),
        confidence=_confidence(len(above) + len(below)),
    )


def _analyze_cadence(videos: list[dict], derived) -> CadenceFindings:
    dated = sum(
        1
        for v in videos
        if derived.videos[v["video_id"]].get("upload_age_days") is not None
    )
    cv = derived.channel.get("upload_interval_cv")
    return CadenceFindings(
        sample_size=dated,
        median_interval_days=derived.channel.get("median_upload_interval_days"),
        max_interval_days=derived.channel.get("max_upload_interval_days"),
        consistency_cv=cv,
        regularity=_regularity(cv),
        confidence=_confidence(dated),
    )


def analyze_channel(
    channel: str, db_path: Path = DB_PATH, now: datetime | None = None
) -> ChannelFindings:
    """Analyze one ingested channel and return canonical findings (Q1/Q2/Q3).

    ``channel`` is a stored ``channel_id`` or ``handle``. ``now`` is injectable so that
    age-based analysis is deterministic in tests. Returns a ``ChannelFindings``.
    """
    now = now or datetime.now(UTC)
    raw_channel, videos = _load_channel(channel, db_path)
    derived = compute(raw_channel, videos, now=now)
    return ChannelFindings(
        channel=ChannelRef(
            channel_id=raw_channel["channel_id"],
            title=raw_channel.get("title"),
            handle=raw_channel.get("handle"),
            url=raw_channel.get("url"),
            subscriber_count=raw_channel.get("subscriber_count"),
        ),
        sample_size=len(videos),
        outliers=_analyze_outliers(videos, derived),
        titles=_analyze_titles(videos, derived),
        cadence=_analyze_cadence(videos, derived),
    )
