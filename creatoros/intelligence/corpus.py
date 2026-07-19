"""Corpus evidence: turning per-video token lists into recurring-phrase findings.

This is the *pattern* layer of RFC-002 (Level 2): the metrics engine derived a video's
tokens (Level-1 facts); here the intelligence layer finds what recurs *across* videos.
Everything is deterministic — n-gram counting, document frequency, a support floor — and
descriptive: it reports what recurs and where, never why. No LLM.

A phrase counts once per video (document frequency), because recurrence across videos is
what makes an observation stronger evidence (RFC-002), not raw repetition inside one
talkative video. A phrase must clear a support floor to be reported; below that, noise,
not evidence (Part D — evidence only if it answers a question).

Phrases are *grouped* by a normalised key ("story"/"stories" are one phrase) but *shown*
in the spelling the creator actually used most — the reader should see their own words,
not a stemmer's output.
"""

from __future__ import annotations

import math

from creatoros.intelligence.findings import CorpusPhrase
from creatoros.intelligence.strength import ORDER, phrase_strength
from creatoros.metrics.text import (
    NUMBER_PLACEHOLDER,
    is_content_word,
    is_stopword,
    normalize_key,
)

# The n-gram sizes considered. Unigrams surface *keywords* (content words only);
# bigrams and trigrams surface recurring *phrases* and hooks ("in this video").
_SIZES = (1, 2, 3)

# A phrase must recur in at least this share of contributing videos (floored at 2) to
# count as evidence. One video is never "recurring"; the ratio keeps the bar meaningful
# as the corpus grows (RFC-002: repetition across many observations).
_MIN_SUPPORT_RATIO = 0.10
_MIN_SUPPORT_FLOOR = 2

# The above/below split is only shown when each side has at least this many contributing
# videos — below it a proportion is noise, so the split is withheld rather than invented
# (issue #47 answered honestly, not exaggerated; Part F).
_MIN_GROUP_FOR_SPLIT = 4

# ...and only when the split actually *says* something. A phrase must appear in at least
# this many of the grouped videos and lean at least this far to one side before the
# columns earn their place. Without this, most channels render two columns of "0 of 12 /
# 1 of 12" — technically true, informative of nothing (Part G).
_MIN_SPLIT_OCCURRENCES = 4
_MIN_SPLIT_GAP = 2

# Cap on phrases reported per family, so the strongest recurrence leads and the report
# stays an investigator's summary, not a concordance (Part G).
_MAX_PHRASES = 6


def _key(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """The grouping key for a phrase: each token reduced to its normalised form."""
    return tuple(normalize_key(t) for t in tokens)


def _ngrams(tokens: list[str], size: int) -> set[tuple[str, ...]]:
    """The *set* of contiguous ``size``-grams in ``tokens`` (deduplicated per video).

    Function-word-only phrases carry no signal and are dropped: a unigram must be a
    content word; a longer n-gram must contain at least one content word (so "in this
    video" survives on "video" but "of the" does not).

    Phrases that are mostly the number placeholder are also dropped: "# years old" is a
    real recurring device, but "# a #" is an artefact of normalisation, not language.
    """
    grams: set[tuple[str, ...]] = set()
    for i in range(len(tokens) - size + 1):
        gram = tuple(tokens[i : i + size])
        if gram.count(NUMBER_PLACEHOLDER) * 2 > size:
            continue
        if size == 1:
            if is_content_word(gram[0]):
                grams.add(gram)
        elif not all(is_stopword(t) for t in gram):
            grams.add(gram)
    return grams


def _video_grams(tokens: list[str] | None) -> dict[tuple[str, ...], tuple[str, ...]]:
    """Map each phrase key in one video to the surface form it appeared as."""
    if not tokens:
        return {}
    surfaces: dict[tuple[str, ...], tuple[str, ...]] = {}
    for size in _SIZES:
        for gram in _ngrams(tokens, size):
            surfaces.setdefault(_key(gram), gram)
    return surfaces


def _is_redundant(
    candidate: tuple[str, ...],
    count: int,
    kept: list[tuple[tuple[str, ...], int]],
) -> bool:
    """Whether a shorter phrase is subsumed by an already-kept longer one.

    "this video" adds nothing once "in this video" is reported with the same document
    count — it is the same recurrence seen through a smaller window. Drop the shorter
    phrase when it is a contiguous slice of a kept longer phrase with an equal count
    (Part D — hide non-informative, redundant rows).
    """
    for phrase, phrase_count in kept:
        if len(phrase) <= len(candidate) or phrase_count != count:
            continue
        window = len(candidate)
        if any(
            phrase[i : i + window] == candidate for i in range(len(phrase) - window + 1)
        ):
            return True
    return False


def recurring_phrases(
    tokens_by_video: dict[str, list[str] | None],
    above_ids: set[str],
    below_ids: set[str],
) -> tuple[list[CorpusPhrase], int, int, int]:
    """Recurring phrases across a token family, with an optional above/below split.

    Returns ``(phrases, basis_n, above_n, below_n)`` where ``basis_n`` is the number of
    videos that contributed any tokens and the group sizes are those *among contributing
    videos* (zero when the split was withheld). Phrases are ranked by strength, then
    document count, then n-gram length (longest first, so the most specific recurrence
    leads), then alphabetically for a deterministic order.
    """
    grams_by_video = {
        vid: _video_grams(tokens) for vid, tokens in tokens_by_video.items()
    }
    contributing = [vid for vid, tokens in tokens_by_video.items() if tokens]
    basis_n = len(contributing)
    if basis_n == 0:
        return [], 0, 0, 0

    # Round *up*: at 25 videos, rounding down puts the floor at 2, and a phrase in two
    # of twenty-five videos is not a habit (Part G).
    min_support = max(_MIN_SUPPORT_FLOOR, math.ceil(_MIN_SUPPORT_RATIO * basis_n))
    document_count: dict[tuple[str, ...], int] = {}
    surface_counts: dict[tuple[str, ...], dict[tuple[str, ...], int]] = {}
    for vid in contributing:
        for key, surface in grams_by_video[vid].items():
            document_count[key] = document_count.get(key, 0) + 1
            seen = surface_counts.setdefault(key, {})
            seen[surface] = seen.get(surface, 0) + 1

    above_basis = [v for v in above_ids if tokens_by_video.get(v)]
    below_basis = [v for v in below_ids if tokens_by_video.get(v)]
    show_split = (
        len(above_basis) >= _MIN_GROUP_FOR_SPLIT
        and len(below_basis) >= _MIN_GROUP_FOR_SPLIT
    )

    candidates = [
        (key, count) for key, count in document_count.items() if count >= min_support
    ]
    ranked = sorted(
        candidates,
        key=lambda item: (
            -ORDER[phrase_strength(item[1], item[1] / basis_n, basis_n)],
            -item[1],
            -len(item[0]),
            item[0],
        ),
    )

    selected: list[tuple[tuple[str, ...], int]] = []
    kept: list[tuple[tuple[str, ...], int]] = []
    for key, count in ranked:
        if _is_redundant(key, count, kept):
            continue
        selected.append((key, count))
        kept.append((key, count))
        if len(selected) >= _MAX_PHRASES:
            break

    splits = {
        key: (
            sum(1 for v in above_basis if key in grams_by_video[v]),
            sum(1 for v in below_basis if key in grams_by_video[v]),
        )
        for key, _ in selected
    }
    # Keep the split only if at least one phrase leans decisively. Otherwise every row
    # would read "0 of 12 / 1 of 12" — two columns that inform nothing (Part G).
    informative = show_split and any(
        above + below >= _MIN_SPLIT_OCCURRENCES and abs(above - below) >= _MIN_SPLIT_GAP
        for above, below in splits.values()
    )

    phrases: list[CorpusPhrase] = []
    for key, count in selected:
        # Show the creator their own wording: the surface spelling seen in the most
        # videos, ties broken alphabetically so the choice is deterministic.
        surface = min(
            surface_counts[key].items(), key=lambda item: (-item[1], item[0])
        )[0]
        ratio = count / basis_n
        above_count, below_count = splits[key]
        phrases.append(
            CorpusPhrase(
                text=" ".join(surface),
                size=len(key),
                document_count=count,
                document_ratio=ratio,
                above_count=above_count if informative else None,
                below_count=below_count if informative else None,
                strength=phrase_strength(count, ratio, basis_n),
            )
        )
    if not informative:
        return phrases, basis_n, 0, 0
    return phrases, basis_n, len(above_basis), len(below_basis)
