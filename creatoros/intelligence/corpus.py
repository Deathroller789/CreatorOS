"""Corpus evidence: turning per-video token lists into recurring-phrase findings.

This is the *pattern* layer of RFC-002 (Level 2): the metrics engine derived a video's
tokens (Level-1 facts); here the intelligence layer finds what recurs *across* videos.
Everything is deterministic — n-gram counting, document frequency, a support floor — and
descriptive: it reports what recurs and where, never why. No LLM.

A phrase counts once per video (document frequency), because recurrence across videos is
what makes an observation stronger evidence (RFC-002), not raw repetition inside one
talkative video. A phrase must clear a support floor to be reported; below that, noise,
not evidence (Part D — evidence only if it answers a question).
"""

from __future__ import annotations

from creatoros.intelligence.findings import CorpusPhrase
from creatoros.metrics.text import is_content_word, is_stopword

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

# Cap on phrases reported per family, so the strongest recurrence leads and the report
# stays an investigator's summary, not a concordance.
_MAX_PHRASES = 8


def _ngrams(tokens: list[str], size: int) -> set[tuple[str, ...]]:
    """The *set* of contiguous ``size``-grams in ``tokens`` (deduplicated per video).

    Function-word-only phrases carry no signal and are dropped: a unigram must be a
    content word; a longer n-gram must contain at least one content word (so "in this
    video" survives on "video" but "of the" does not).
    """
    grams: set[tuple[str, ...]] = set()
    for i in range(len(tokens) - size + 1):
        gram = tuple(tokens[i : i + size])
        if size == 1:
            if is_content_word(gram[0]):
                grams.add(gram)
        elif not all(is_stopword(t) for t in gram):
            grams.add(gram)
    return grams


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
) -> tuple[list[CorpusPhrase], int]:
    """Recurring phrases across a token family, with an optional above/below split.

    Returns ``(phrases, basis_n)`` where ``basis_n`` is the number of videos that
    contributed any tokens. Phrases are ranked by document count (desc), then by n-gram
    length (desc, so the most specific recurrence leads), then alphabetically for a
    deterministic order.
    """
    grams_by_video: dict[str, set[tuple[str, ...]]] = {
        vid: set().union(*(_ngrams(tokens, n) for n in _SIZES)) if tokens else set()
        for vid, tokens in tokens_by_video.items()
    }
    contributing = [vid for vid, tokens in tokens_by_video.items() if tokens]
    basis_n = len(contributing)
    if basis_n == 0:
        return [], 0

    min_support = max(_MIN_SUPPORT_FLOOR, round(_MIN_SUPPORT_RATIO * basis_n))
    document_count: dict[tuple[str, ...], int] = {}
    for vid in contributing:
        for gram in grams_by_video[vid]:
            document_count[gram] = document_count.get(gram, 0) + 1

    ranked = sorted(
        (
            (gram, count)
            for gram, count in document_count.items()
            if count >= min_support
        ),
        key=lambda item: (-item[1], -len(item[0]), item[0]),
    )

    above_basis = [v for v in above_ids if tokens_by_video.get(v)]
    below_basis = [v for v in below_ids if tokens_by_video.get(v)]
    show_split = (
        len(above_basis) >= _MIN_GROUP_FOR_SPLIT
        and len(below_basis) >= _MIN_GROUP_FOR_SPLIT
    )

    phrases: list[CorpusPhrase] = []
    kept: list[tuple[tuple[str, ...], int]] = []
    for gram, count in ranked:
        if _is_redundant(gram, count, kept):
            continue
        above_count = (
            sum(1 for v in above_basis if gram in grams_by_video[v])
            if show_split
            else None
        )
        below_count = (
            sum(1 for v in below_basis if gram in grams_by_video[v])
            if show_split
            else None
        )
        phrases.append(
            CorpusPhrase(
                text=" ".join(gram),
                size=len(gram),
                document_count=count,
                document_ratio=count / basis_n,
                above_count=above_count,
                below_count=below_count,
            )
        )
        kept.append((gram, count))
        if len(phrases) >= _MAX_PHRASES:
            break
    return phrases, basis_n
