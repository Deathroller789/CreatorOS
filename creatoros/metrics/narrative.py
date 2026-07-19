"""Narrative-structure metrics: deterministic feature extraction from transcripts.

RFC-002 names narrative the most valuable and most expensive evidence class, and draws
honest line through it: the *signals* are countable (Level 1–2 evidence), the *verdict*
("a strong hook") is Level-4 synthesis and is not produced here. This module implements
only the signals — fixed lexicon counts, rates per 1,000 words, and simple positional
checks. No classification, no scoring, no inference, no LLM (ADR-011).

Every metric carries ``category="narrative"``, so the intelligence layer discovers the
whole family and compares it across the performance split with no code change (ADR-006).
A video without a transcript yields ``None`` throughout and simply drops out (ADR-009).

Rates are per 1,000 words so a 40-minute documentary and a 5-minute explainer are
comparable; raw counts would only re-measure length.
"""

from __future__ import annotations

from creatoros.metrics import lexicon
from creatoros.metrics.engine import metric
from creatoros.metrics.text import clean_text

# The leading / trailing region treated as the "opening" and "ending". Wide enough to
# contain a hook or a sign-off, narrow enough that mid-video language cannot leak in.
_OPENING_WORDS = 60
_CLOSING_WORDS = 60

# Rates are quoted per this many words.
_PER = 1_000.0

# Below this many words a transcript is a fragment (a stub track, a music video),
# and a rate computed from it is noise. Such videos drop out rather than distort.
_MIN_WORDS = 50


def _usable(transcript_tokens: list[str] | None) -> list[str] | None:
    """The token list if it is long enough to measure, else ``None``.

    Every metric here consumes the ``transcript_tokens`` metric rather than
    re-tokenising the raw text. Tokenising a long transcript is by far the most
    expensive step in the pipeline, and with a dozen narrative signals per video
    doing it independently the cost multiplies. The dependency graph exists to
    share exactly this kind of intermediate derivation (ADR-006).
    """
    if not transcript_tokens or len(transcript_tokens) < _MIN_WORDS:
        return None
    return transcript_tokens


def _rate(tokens: list[str], vocabulary: frozenset[str]) -> float:
    """Occurrences of ``vocabulary`` per 1,000 tokens."""
    hits = sum(1 for t in tokens if t in vocabulary)
    return hits * _PER / len(tokens)


def _lexicon_metric(name: str, vocabulary: frozenset[str], doc: str):
    """Register a per-1,000-word rate metric over a lexicon.

    The lexicon metrics are identical but for their word list, so they come from one
    definition rather than copy-pasted — the engine still sees ordinary registered pure
    functions with declared dependencies.
    """

    def fn(transcript_tokens: list[str] | None) -> float | None:
        tokens = _usable(transcript_tokens)
        return None if tokens is None else _rate(tokens, vocabulary)

    fn.__name__ = name
    fn.__doc__ = doc
    return metric(
        scope="video",
        unit="per 1k words",
        depends_on=("transcript_tokens",),
        category="narrative",
    )(fn)


curiosity_word_rate = _lexicon_metric(
    "curiosity_word_rate",
    lexicon.CURIOSITY,
    "How often the narration opens a curiosity gap (secret, hidden, mystery...).",
)
urgency_word_rate = _lexicon_metric(
    "urgency_word_rate",
    lexicon.URGENCY,
    "How often the narration presses on time (immediately, suddenly, crisis...).",
)
authority_word_rate = _lexicon_metric(
    "authority_word_rate",
    lexicon.AUTHORITY,
    "How often the narration cites external credibility (study, research, expert...).",
)
conflict_word_rate = _lexicon_metric(
    "conflict_word_rate",
    lexicon.CONFLICT,
    "How often the narration names tension or things going wrong.",
)
resolution_word_rate = _lexicon_metric(
    "resolution_word_rate",
    lexicon.RESOLUTION,
    "How often the narration resolves things (finally, solved, turned out...).",
)
chronology_marker_rate = _lexicon_metric(
    "chronology_marker_rate",
    lexicon.CHRONOLOGY,
    "How often the narration sequences events (then, next, after, eventually...).",
)
reported_speech_rate = _lexicon_metric(
    "reported_speech_rate",
    lexicon.REPORTED_SPEECH,
    "How often the narration quotes people (said, told, asked...) — dialogue density.",
)
second_person_rate = _lexicon_metric(
    "second_person_rate",
    lexicon.SECOND_PERSON,
    "How often the narration addresses the viewer directly (you, your).",
)
first_person_rate = _lexicon_metric(
    "first_person_rate",
    lexicon.FIRST_PERSON,
    "How often the narrator speaks as themselves (I, we, my).",
)


@metric(
    scope="video",
    unit="0/1",
    depends_on=("transcript_text", "transcript_tokens"),
    category="narrative",
)
def opening_is_question(
    transcript_text: str | None, transcript_tokens: list[str] | None
) -> int | None:
    """Whether the video opens by asking something.

    A literal '?' in the opening counts; so does a question word in the first tokens,
    because auto-generated caption tracks routinely carry no punctuation at all.
    """
    tokens = _usable(transcript_tokens)
    if tokens is None:
        return None
    cleaned = clean_text(transcript_text)
    opening_text = " ".join(cleaned.split()[:_OPENING_WORDS])
    if "?" in opening_text:
        return 1
    return int(any(t in lexicon.QUESTION_WORDS for t in tokens[:12]))


@metric(
    scope="video",
    unit="0/1",
    depends_on=("transcript_tokens",),
    category="narrative",
)
def opening_is_command(transcript_tokens: list[str] | None) -> int | None:
    """Whether the video opens on an imperative ("Imagine...", "Picture this...")."""
    tokens = _usable(transcript_tokens)
    if tokens is None:
        return None
    return int(bool(tokens) and tokens[0] in lexicon.IMPERATIVE_OPENERS)


@metric(
    scope="video",
    unit="0/1",
    depends_on=("transcript_tokens",),
    category="narrative",
)
def opening_addresses_viewer(transcript_tokens: list[str] | None) -> int | None:
    """Whether the opening speaks directly to the viewer ("you")."""
    tokens = _usable(transcript_tokens)
    if tokens is None:
        return None
    return int(any(t in lexicon.SECOND_PERSON for t in tokens[:_OPENING_WORDS]))


@metric(
    scope="video",
    unit="per 1k words",
    depends_on=("transcript_tokens",),
    category="narrative",
)
def cta_rate(transcript_tokens: list[str] | None) -> float | None:
    """How often the video asks for something (subscribe, comment, link below).

    Fixed phrases, not single words: "like" and "channel" are far too common in ordinary
    speech to count as a call to action.
    """
    tokens = _usable(transcript_tokens)
    if tokens is None:
        return None
    hits = 0
    for phrase in lexicon.CTA_PHRASES:
        span = len(phrase)
        hits += sum(
            1
            for i in range(len(tokens) - span + 1)
            if tuple(tokens[i : i + span]) == phrase
        )
    return hits * _PER / len(tokens)


@metric(
    scope="video",
    unit="ratio",
    depends_on=("transcript_tokens",),
    category="narrative",
)
def callback_overlap(transcript_tokens: list[str] | None) -> float | None:
    """Share of the ending's distinct content words that also appeared in the opening.

    A deterministic proxy for a callback: an ending that returns to the language it
    opened with. It measures word reuse between the two ends of the video and nothing
    more — whether that reuse *lands* as a satisfying callback is not decided here.
    """
    tokens = _usable(transcript_tokens)
    if tokens is None:
        return None
    from creatoros.metrics.text import is_content_word

    opening = {t for t in tokens[:_OPENING_WORDS] if is_content_word(t)}
    closing = {t for t in tokens[-_CLOSING_WORDS:] if is_content_word(t)}
    if not closing:
        return None
    return len(opening & closing) / len(closing)


@metric(
    scope="video",
    unit="words/minute",
    depends_on=("transcript_tokens", "duration"),
    category="narrative",
)
def speech_pace(
    transcript_tokens: list[str] | None, duration: int | None
) -> float | None:
    """Spoken words per minute — how densely the video talks."""
    tokens = _usable(transcript_tokens)
    if tokens is None or not duration:
        return None
    return len(tokens) / (duration / 60.0)
