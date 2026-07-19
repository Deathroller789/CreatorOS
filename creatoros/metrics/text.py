"""Deterministic text primitives for corpus evidence — pure, dependency-free.

Tokenisation lives in the metrics layer because it *derives* a fact (the tokens of a
title or transcript) from raw text, deterministically and reproducibly (ADR-006, RFC-002
Level-1 evidence). Finding *recurring* structure across tokens is a different act, a
pattern across many videos, and belongs to the intelligence layer, not here.

Normalisation is what separates useful phrase evidence from noise. Raw captions differ
from human ones in punctuation, fillers, and annotations; the same phrase appears as
"Top 5 stories" and "Top 10 stories"; the same word appears as "story" and "stories".
Each normalisation below exists to make genuinely-recurring language *look* recurring,
and every one is a fixed rule — no model, no statistics, no LLM. Raw text is never
mutated in storage: this is a derivation, recomputed on demand (ADR-010).
"""

from __future__ import annotations

import re

# Caption annotations describing sound rather than speech: "[Music]", "(upbeat music)",
# "♪". They are not the creator's words, and left in they dominate recurring-phrase
# evidence (every video "says" music). Removed before tokenising.
_ANNOTATION_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|♪+")

# Speaker-change markers in auto-caption tracks. Structural, not spoken.
_SPEAKER_RE = re.compile(r">>+|&gt;&gt;")

# Apostrophes are deleted (not split on) so a contraction stays one token: "don't" ->
# "dont", "I'm" -> "im" — else n-grams fragment into "i m going". Covers straight and
# both curly apostrophes. Everything else non-alphanumeric is a token boundary.
_APOSTROPHES = str.maketrans("", "", "'’‘")
_TOKEN_RE = re.compile(r"[^\w]+", flags=re.UNICODE)

# Any run of digits collapses to one placeholder, so "Top 5 Scary Stories" and "Top 10
# Scary Stories" are recognised as the *same* recurring format. The specific number is
# rarely the pattern; the fact that a number is there is.
NUMBER_PLACEHOLDER = "#"
_DIGITS_RE = re.compile(r"^\d+(?:st|nd|rd|th)?$")

# Speech disfluencies that auto-generated captions transcribe literally. They are not
# language a creator chose, and they crowd out real phrases in the n-gram counts.
_FILLERS: frozenset[str] = frozenset(
    "uh uhh uhm um umm erm hmm mmm mhm eh".split()  # noqa: SIM905
)

# Contraction spellings that differ between human and auto captions for the *same*
# spoken words. Mapped to one form so the phrase matches across both (e.g. a manual
# track's "do not" and an auto track's "don't" -> "dont").
_CONTRACTIONS: dict[str, str] = {
    "do not": "dont",
    "does not": "doesnt",
    "did not": "didnt",
    "is not": "isnt",
    "are not": "arent",
    "was not": "wasnt",
    "will not": "wont",
    "can not": "cant",
    "cannot": "cant",
    "could not": "couldnt",
    "would not": "wouldnt",
    "should not": "shouldnt",
    "have not": "havent",
    "has not": "hasnt",
    "it is": "its",
    "that is": "thats",
    "there is": "theres",
    "you are": "youre",
    "we are": "were",
    "they are": "theyre",
    "i am": "im",
    "going to": "gonna",
    "want to": "wanna",
    "got to": "gotta",
}
_MAX_CONTRACTION_WORDS = 2

# Words carrying no topical signal on their own, in three groups: closed-class function
# words; pronoun/negation contractions (which survive apostrophe-collapsing as real
# tokens); and high-frequency discourse fillers ("like", "just", "actually") that are
# common enough in speech to outrank every genuine phrase if left in.
#
# Deliberately *excludes* question and framing words — "how", "why", "what", "when",
# "who", "which", "does", "do", "can", "should", "would" — because "how to", "why you",
# "what happens" are exactly the recurring title/opening hooks corpus evidence exists to
# surface. An n-gram is dropped only when *every* token is a stop word (see
# intelligence.corpus), so "in this video" (video is content) and "dont forget to
# subscribe" (forget, subscribe) both survive.
STOPWORDS: frozenset[str] = frozenset(
    # A whitespace-delimited word list, kept as prose rather than a list literal.
    """
    a an and are as at be been being but by for from had has have he her hers him his
    i if in into is it its me my of on or our ours she so than that the their theirs
    them then there these they this to too up us was were will with you your yours

    im youre hes shes its were theyre thats theres ive id ill weve youve theyve
    dont doesnt didnt isnt arent wasnt wont cant couldnt wouldnt shouldnt hasnt havent

    like just really actually know well okay yeah right thing things kind sort lot
    mean means going get got make makes even still much many one very back come came
    """.split()  # noqa: SIM905
)

# Below this length a unigram is almost never a meaningful keyword ("s", "ll" from
# contraction fragments). N-grams are exempt — a short word inside a phrase is fine.
_MIN_KEYWORD_LEN = 3


def clean_text(text: str | None) -> str:
    """Strip caption annotations, speaker markers, and collapse whitespace.

    Applied before tokenising transcripts so sound annotations and structural markers
    never become "recurring phrases". Idempotent and purely textual.
    """
    if not text:
        return ""
    text = _ANNOTATION_RE.sub(" ", text)
    text = _SPEAKER_RE.sub(" ", text)
    return " ".join(text.split())


def _apply_contractions(tokens: list[str]) -> list[str]:
    """Collapse multi-word contraction spellings to their single-token equivalent."""
    out: list[str] = []
    i = 0
    while i < len(tokens):
        matched = False
        for span in range(_MAX_CONTRACTION_WORDS, 0, -1):
            phrase = " ".join(tokens[i : i + span])
            replacement = _CONTRACTIONS.get(phrase)
            if replacement is not None:
                out.append(replacement)
                i += span
                matched = True
                break
        if not matched:
            out.append(tokens[i])
            i += 1
    return out


def tokenize(text: str | None) -> list[str]:
    """Normalised tokens of ``text``, in order.

    Lower-cased, annotation-stripped, apostrophe-collapsed, digits reduced to ``#``,
    fillers and contraction spellings normalised. Returns ``[]`` for blank input, so a
    video with no transcript simply contributes nothing rather than raising.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []
    raw = _TOKEN_RE.split(cleaned.lower().translate(_APOSTROPHES))
    tokens = [
        NUMBER_PLACEHOLDER if _DIGITS_RE.match(t) else t
        for t in raw
        if t and t not in _FILLERS
    ]
    return _apply_contractions(tokens)


def normalize_key(token: str) -> str:
    """A conservative singular form, used to *group* phrases that differ only in number.

    "stories"/"story" and "tricks"/"trick" should count as one recurring phrase. The
    rules are deliberately timid — they never touch short words, double-s endings, or
    known -us/-is nouns — because over-stemming ("this" -> "thi") destroys more evidence
    than it merges. Grouping only: the phrase is *displayed* in its commonest real
    spelling, never in this reduced form.
    """
    if len(token) <= 3 or not token.isalpha():
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith(("sses", "shes", "ches", "xes", "zes")):
        return token[:-2]
    if token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def is_stopword(token: str) -> bool:
    """Whether ``token`` is a closed-class function word carrying no topical signal."""
    return token in STOPWORDS


def is_content_word(token: str) -> bool:
    """A token usable as a standalone keyword: long enough and not a stop word."""
    return len(token) >= _MIN_KEYWORD_LEN and token not in STOPWORDS
