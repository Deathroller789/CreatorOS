"""Deterministic text primitives for corpus evidence — pure, dependency-free.

Tokenisation lives in the metrics layer because it *derives* a fact (the tokens of a
title or transcript) from raw text, deterministically and reproducibly (ADR-006, RFC-002
Level-1 evidence). Finding *recurring* structure across tokens is a different act, a
pattern across many videos, and belongs to the intelligence layer, not here.

No LLM, no external dependency: just Unicode-aware splitting and a small closed-class
stop-word set. The same text always yields the same tokens.
"""

from __future__ import annotations

import re

# Apostrophes are deleted (not split on) so a contraction stays one token: "don't" ->
# "dont", "I'm" -> "im" — else n-grams fragment into "i m going". Covers straight and
# both curly apostrophes. Everything else non-alphanumeric is a token boundary.
_APOSTROPHES = str.maketrans("", "", "'’‘")
_TOKEN_RE = re.compile(r"[^\w]+", flags=re.UNICODE)

# Closed-class function words that carry no topical signal on their own. Deliberately
# *excludes* question and framing words — "how", "why", "what", "when", "who", "which",
# "does", "do", "can", "should", "would" — because "how to", "why you", "what happens"
# are exactly the recurring title/opening hooks corpus evidence exists to surface. An
# n-gram is dropped only when *every* token is a stop word (see intelligence.corpus), so
# "in this video" (video is content) and "how to" (kept word) both survive.
STOPWORDS: frozenset[str] = frozenset(
    # A whitespace-delimited word list, kept as prose rather than a list literal.
    """
    a an and are as at be been being but by for from had has have he her hers him his
    i if in into is it its me my of on or our ours she so than that the their theirs
    them then there these they this to too up us was were will with you your yours
    """.split()  # noqa: SIM905
)

# Below this length a unigram is almost never a meaningful keyword ("s", "ll" from
# contraction fragments). N-grams are exempt — a short word inside a phrase is fine.
_MIN_KEYWORD_LEN = 3


def tokenize(text: str | None) -> list[str]:
    """Lower-case, split on non-alphanumeric runs, and drop empties. Order preserved.

    Returns ``[]`` for ``None`` or blank input, so a video with no transcript simply
    contributes nothing rather than raising.
    """
    if not text:
        return []
    return [t for t in _TOKEN_RE.split(text.lower().translate(_APOSTROPHES)) if t]


def is_stopword(token: str) -> bool:
    """Whether ``token`` is a closed-class function word carrying no topical signal."""
    return token in STOPWORDS


def is_content_word(token: str) -> bool:
    """A token usable as a standalone keyword: long enough and not a stop word."""
    return len(token) >= _MIN_KEYWORD_LEN and token not in STOPWORDS
