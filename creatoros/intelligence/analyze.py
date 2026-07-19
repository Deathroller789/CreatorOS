"""Channel Intelligence: discover evidence from metrics and return findings.

Layer discipline (docs/modules/002-channel-intelligence.md): this module sits above the
metrics engine and consumes only **derived** metrics for its conclusions. It loads raw
rows from SQLite solely to feed the engine (ADR-006); it never does arithmetic on a raw
field, and it never produces any output format — that is the reporting layer's job.

Evidence is *discovered*, not hard-coded (ADR-006, RFC-002): the layer asks the registry
which evidence families exist — scalar families become above/below comparisons, corpus
families become recurring-phrase findings — so adding a metric family grows the analysis
with no change here. Deterministic throughout; no LLM. Explanations (why) are never
produced — only the evidence a later synthesis could be held accountable to.
"""

from __future__ import annotations

import contextlib
import sqlite3
import statistics
from datetime import UTC, datetime
from pathlib import Path

from creatoros.intelligence.corpus import recurring_phrases
from creatoros.intelligence.findings import (
    CadenceFindings,
    ChannelFindings,
    ChannelRef,
    Confidence,
    CorpusGroup,
    FeatureComparison,
    FeatureGroup,
    OutlierFindings,
    VideoOutlier,
)
from creatoros.intelligence.strength import (
    ORDER,
    WEAK,
    comparison_strength,
    is_negligible,
)
from creatoros.metrics import compute, evidence_categories, registry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / "database" / "creatoros.db"

# Within this window of upload, views/day is still inflated by the launch spike and may
# not hold, so a fresh video should not be read as a settled outlier. Flagged in the
# ranking, never dropped — the reader decides. (The baseline excludes them upstream, in
# the ``settled_views_per_day`` metric.)
RECENT_DAYS = 7.0

# Cohen's d is unstable when a group is tiny: it can read as an enormous effect from a
# handful of videos (issue #42 — d=-3.45 from 2 vs 2, beside a "low confidence" label).
# Below this per-group size we withhold the effect size; the group means and their
# difference still render as descriptive facts, but the statistic is not made up.
MIN_GROUP_FOR_EFFECT_SIZE = 5

# Below this many ranked videos there is not enough spread to carve quantiles from, so
# the split falls back to the channel baseline (see ``_performance_groups``).
MIN_VIDEOS_FOR_QUANTILE = 12

# The share taken from each end when quantile grouping applies.
QUANTILE_SHARE = 0.25

# At most this many comparisons per family. Ranked by strength, so what survives is what
# most separates the groups — a shorter, more informative table (Part G).
MAX_FEATURES_PER_GROUP = 6

# Creator-facing names. Everything a creator reads should be in their language, not the
# registry's (Part D). A metric with no entry falls back to its registry name, so a new
# metric still renders — it just reads like code until it is named here.
_FEATURE_LABELS = {"title": "Title patterns", "narrative": "Storytelling patterns"}
_METRIC_LABELS = {
    "title_length": "Title length",
    "title_word_count": "Words in title",
    "title_has_number": "Title contains a number",
    "title_starts_with_number": "Title starts with a number",
    "title_has_question": "Title asks a question",
    "title_has_colon": "Title uses a colon",
    "title_has_brackets": "Title uses brackets",
    "title_caps_ratio": "Title written in capitals",
    "curiosity_word_rate": "Curiosity language (secret, hidden, mystery)",
    "urgency_word_rate": "Urgency language (suddenly, immediately)",
    "authority_word_rate": "Sourcing language (study, research, expert)",
    "conflict_word_rate": "Conflict language (problem, danger, failed)",
    "resolution_word_rate": "Resolution language (finally, solved)",
    "chronology_marker_rate": "Sequencing words (then, next, after)",
    "reported_speech_rate": "Quoting people (said, told, asked)",
    "second_person_rate": "Speaking to the viewer (you)",
    "first_person_rate": "Speaking as yourself (I, we)",
    "opening_is_question": "Opens with a question",
    "opening_is_command": "Opens with a command",
    "opening_addresses_viewer": "Opening speaks to the viewer",
    "cta_rate": "Calls to action",
    "callback_overlap": "Ending echoes the opening",
    "speech_pace": "Speaking pace",
}
_CORPUS_LABELS = {
    "title_tokens": "Words you reuse in titles",
    "transcript_opening_tokens": "How you open",
    "transcript_closing_tokens": "How you close",
    "transcript_tokens": "Phrases you repeat",
}
# The order corpus families read in the report: title, then opening → ending → whole.
_CORPUS_ORDER = {
    "title_tokens": 0,
    "transcript_opening_tokens": 1,
    "transcript_closing_tokens": 2,
    "transcript_tokens": 3,
}


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
    """Standardized mean difference between two groups; None if too few to estimate.

    Requires ``MIN_GROUP_FOR_EFFECT_SIZE`` per group: below that the statistic is noise
    wearing a decimal point (issue #42), so it is withheld rather than reported.
    """
    if len(above) < MIN_GROUP_FOR_EFFECT_SIZE or len(below) < MIN_GROUP_FOR_EFFECT_SIZE:
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
    """Load the raw channel row and its videos. The module's single raw-I/O boundary.

    Each video is given a ``transcript_text`` field (``None`` when no transcript was
    captured) so the corpus metrics get a stable field. Present but empty (never a
    missing key) is how "no transcript" is represented (ADR-009).
    """
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
        # Transcripts live in their own table and may be absent entirely (older or test
        # databases). Missing table or missing row both mean "no transcript" — quietly.
        transcripts: dict[str, str | None] = {}
        with contextlib.suppress(sqlite3.OperationalError):
            transcripts = {
                r["video_id"]: r["text"]
                for r in conn.execute("SELECT video_id, text FROM transcripts")
            }
    finally:
        conn.close()
    if not videos:
        raise IntelligenceError(f"channel {channel!r} has no stored videos")
    for v in videos:
        v["transcript_text"] = transcripts.get(v["video_id"])
    return raw_channel, videos


def _performance_groups(
    videos: list[dict], derived, quantile: bool | None = None
) -> tuple[set[str], set[str], str]:
    """The two groups every comparison contrasts, plus a plain description of them.

    Two strategies, chosen by sample size:

    - **Quantile** (enough videos): the top and bottom quarter by performance, with the
      middle deliberately discarded. The middle is where videos differ least,
      so including it blunts every contrast; dropping it compares the clear cases.
    - **Baseline** (small samples): at/above the channel baseline versus below it. With
      few videos a quarter is one or two of them, and discarding the middle would leave
      nothing — so the whole sample is used and the contrast is simply weaker.

    ``quantile`` forces a strategy; the default picks by size. Deterministic either way:
    ties are broken by video id so the same sample always yields the same groups.
    """
    ranked = sorted(
        (
            (v["video_id"], derived.videos[v["video_id"]]["performance_index"])
            for v in videos
            if derived.videos[v["video_id"]].get("performance_index") is not None
        ),
        key=lambda pair: (-pair[1], pair[0]),
    )
    n = len(ranked)
    use_quantile = n >= MIN_VIDEOS_FOR_QUANTILE if quantile is None else quantile
    if use_quantile and n >= 2:
        size = max(1, int(n * QUANTILE_SHARE))
        above = {vid for vid, _ in ranked[:size]}
        below = {vid for vid, _ in ranked[-size:]}
        return above, below, f"top {size} vs bottom {size} of {n} videos"
    above = {vid for vid, index in ranked if index >= 1.0}
    below = {vid for vid, index in ranked if index < 1.0}
    return above, below, "above vs below the channel baseline"


def _analyze_outliers(videos: list[dict], derived) -> OutlierFindings:
    baseline = derived.channel.get("baseline_views_per_day")
    basis_n = derived.channel.get("baseline_basis_count") or 0
    rated = sum(
        1
        for v in videos
        if derived.videos[v["video_id"]].get("views_per_day") is not None
    )
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
        baseline_iqr_low=derived.channel.get("baseline_iqr_low"),
        baseline_iqr_high=derived.channel.get("baseline_iqr_high"),
        baseline_basis_n=basis_n,
        # Fresh videos held out of the baseline: rated videos minus the basis. Zero when
        # the sample was too small to exclude any (the fallback path in channel.py).
        baseline_excluded_recent=max(rated - basis_n, 0),
        sample_size=len(ranking),
        ranking=tuple(ranking),
        confidence=_confidence(len(ranking)),
    )


def _feature_values(derived, video_ids: set[str], name: str) -> list[float]:
    """Non-null values of a derived metric across a group of videos."""
    return [
        derived.videos[i][name]
        for i in video_ids
        if derived.videos[i].get(name) is not None
    ]


def _feature_groups(
    derived, above: set[str], below: set[str], grouping: str
) -> tuple[FeatureGroup, ...]:
    """One comparison group per scalar evidence family discovered in the registry.

    For each family (``title``, ``narrative``, ...) every metric is contrasted across
    the two performance groups, then filtered hard (Part G): a comparison is dropped
    when the groups do not separate, and when the separation is too small to matter —
    a negligible effect size, or too small a relative difference. What survives is
    ranked by strength and capped, so the table shows what most distinguishes the
    groups rather than everything measurable. An empty family is omitted.
    """
    units = {name: m.unit for name, m in registry().items()}
    sample_size = len(above) + len(below)
    groups: list[FeatureGroup] = []
    for category in evidence_categories("video"):
        if category.startswith("corpus:"):
            continue
        features: list[FeatureComparison] = []
        for name in sorted(registry(category=category)):
            a = _feature_values(derived, above, name)
            b = _feature_values(derived, below, name)
            if not a or not b:
                continue
            above_mean = statistics.fmean(a)
            below_mean = statistics.fmean(b)
            difference = above_mean - below_mean
            if difference == 0:
                continue  # no separation between groups — nothing to report
            scale = max(abs(above_mean), abs(below_mean))
            effect = _cohens_d(a, b)
            if is_negligible(effect, difference / scale if scale else 0.0):
                continue  # real but far too small to be worth a creator's attention
            features.append(
                FeatureComparison(
                    metric=name,
                    label=_METRIC_LABELS.get(name, name),
                    unit=units.get(name, ""),
                    above_mean=above_mean,
                    below_mean=below_mean,
                    difference=difference,
                    effect_size=effect,
                    above_n=len(a),
                    below_n=len(b),
                    strength=comparison_strength(effect, len(a), len(b)),
                )
            )
        if not features:
            continue
        features.sort(
            key=lambda c: (-ORDER[c.strength], -abs(c.effect_size or 0.0), c.metric)
        )
        groups.append(
            FeatureGroup(
                category=category,
                label=_FEATURE_LABELS.get(category, f"{category.title()} patterns"),
                grouping=grouping,
                sample_size=sample_size,
                above_n=len(above),
                below_n=len(below),
                features=tuple(features[:MAX_FEATURES_PER_GROUP]),
                confidence=_confidence(sample_size),
            )
        )
    return tuple(groups)


def _corpus_groups(
    videos: list[dict], derived, above: set[str], below: set[str]
) -> tuple[CorpusGroup, ...]:
    """One recurring-phrase group per corpus family discovered in the registry.

    Each ``corpus:*`` token metric becomes a group; a family whose text is absent for
    every video (no transcripts) yields no phrases and is omitted, with the shortfall
    stated in ``coverage_note`` when text was only partly available (ADR-009).
    """
    sample_size = len(videos)
    corpus_metrics = [
        m
        for m in registry().values()
        if m.scope == "video" and m.category and m.category.startswith("corpus:")
    ]
    groups: list[CorpusGroup] = []
    for m in sorted(
        corpus_metrics, key=lambda m: (_CORPUS_ORDER.get(m.name, 99), m.name)
    ):
        tokens_by_video = {
            v["video_id"]: derived.videos[v["video_id"]].get(m.name) for v in videos
        }
        phrases, basis_n, above_n, below_n = recurring_phrases(
            tokens_by_video, above, below
        )
        if not phrases:
            continue
        if all(p.strength == WEAK for p in phrases):
            # A section where nothing recurs strongly enough to be a habit is a list of
            # coincidences. Better to say nothing than to fill a heading (Part G).
            continue
        note = (
            f"based on {basis_n} of {sample_size} videos with available text"
            if basis_n < sample_size
            else None
        )
        groups.append(
            CorpusGroup(
                category=m.category,
                label=_CORPUS_LABELS.get(m.name, m.category),
                basis_n=basis_n,
                sample_size=sample_size,
                above_n=above_n,
                below_n=below_n,
                phrases=tuple(phrases),
                confidence=_confidence(basis_n),
                coverage_note=note,
            )
        )
    return tuple(groups)


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


def build_findings(raw_channel: dict, videos: list[dict], derived) -> ChannelFindings:
    """Assemble canonical findings from raw rows and their already-computed metrics.

    The pure analysis seam: given the raw channel/videos and the ``derived`` metrics for
    them, discover the evidence and return findings. It touches no DB and computes no
    metric — the metrics engine was already run. Exposed so a caller (e.g. the CLI) can
    orchestrate metrics and intelligence as two distinct, observable steps over data it
    already holds, without a second load.
    """
    above, below, grouping = _performance_groups(videos, derived)
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
        feature_groups=_feature_groups(derived, above, below, grouping),
        corpus_groups=_corpus_groups(videos, derived, above, below),
        cadence=_analyze_cadence(videos, derived),
    )


def analyze_channel(
    channel: str, db_path: Path = DB_PATH, now: datetime | None = None
) -> ChannelFindings:
    """Analyze one ingested channel and return canonical findings.

    ``channel`` is a stored ``channel_id`` or ``handle``. ``now`` is injectable so that
    age-based analysis is deterministic in tests. Returns a ``ChannelFindings``.
    """
    now = now or datetime.now(UTC)
    raw_channel, videos = _load_channel(channel, db_path)
    derived = compute(raw_channel, videos, now=now)
    return build_findings(raw_channel, videos, derived)
