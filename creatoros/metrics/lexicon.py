"""Fixed word lists for deterministic narrative feature extraction.

These are **lexicons, not classifiers**. A metric using them counts how often a creator
reaches for a kind of language; it never decides what a video "is about", never scores
quality, and never infers intent. Counting words in a fixed list is reproducible from
transcript by anyone with this file — RFC-002 Level-1 evidence (ADR-011).

Each list is deliberately small and unambiguous. A word earns its place only if its
presence is hard to read as anything but the category — words common in ordinary
speech ("like", "just", "good") are excluded even when they sometimes carry the signal,
because a lexicon that fires on everything measures nothing.

Scope and honesty: English only, single words (or short fixed phrases where the single
word would be ambiguous). These lists are evidence *inputs*; whether any separates
performance is an empirical question the findings answer, not an assumption made here.
"""

from __future__ import annotations


def _words(text: str) -> frozenset[str]:
    """Build a lexicon from a whitespace-delimited block, kept readable as prose."""
    return frozenset(text.split())


# Language that opens a gap the viewer wants closed — the curiosity hook.
CURIOSITY = _words("""
    secret secrets hidden mystery mysterious unknown unexplained strange bizarre
    weird eerie surprising shocking unbelievable inexplicable puzzling baffling
    revealed uncovered discovery nobody
""")

# Language that presses on time — the urgency lever.
URGENCY = _words("""
    immediately urgent urgently quickly instantly suddenly hurry deadline
    emergency crisis rushing sudden abruptly
""")

# Language that leans on external credibility.
AUTHORITY = _words("""
    study studies research researcher researchers scientist scientists professor
    university published journal evidence data expert experts official officially
    according documented investigators forensic
""")

# Language of tension and things going wrong — the engine of a story's middle.
CONFLICT = _words("""
    problem problems wrong failed failure danger dangerous threat threatened
    attack attacked fight fought against struggle struggled war battle victim
    killed murdered died death missing trapped escape refused
""")

# Language of things resolving — the payoff.
RESOLUTION = _words("""
    finally solved solution answer answered resolved eventually explains
    explained result results conclusion concluded therefore ultimately
    discovered realised realized turned
""")

# Markers that place events in sequence — the spine of narration.
CHRONOLOGY = _words("""
    then next after afterwards before later meanwhile eventually finally first
    second third initially subsequently soon until once during
""")

# Reported-speech verbs — a proxy for dialogue and testimony in narration.
REPORTED_SPEECH = _words("""
    said says told asked replied answered recalled explained described admitted
    claimed insisted whispered shouted
""")

# Direct address to the viewer.
SECOND_PERSON = _words("youre yours yourself yourselves you your")

# The narrator speaking as themselves.
FIRST_PERSON = _words("i im ive id my me mine we our ours us weve were")

# Verbs that open an imperative ("Imagine a room...", "Picture this"). Only counted when
# the transcript's very first word matches, which is what makes it a *command opening*
# rather than an incidental imperative mid-video.
IMPERATIVE_OPENERS = _words("""
    imagine picture think look listen watch stop meet consider remember forget
    welcome take check ask tell try suppose
""")

# Question words, used to detect a question opening when the caption track carries no
# punctuation (auto-generated tracks frequently do not).
QUESTION_WORDS = _words("what why how when where who which whose whom")

# Short fixed phrases for calls to action. Phrases, not single words, because the single
# words ("like", "share", "channel") are far too common in ordinary speech to count.
CTA_PHRASES: tuple[tuple[str, ...], ...] = (
    ("subscribe",),
    ("subscribed",),
    ("subscribing",),
    ("hit", "the", "like"),
    ("leave", "a", "comment"),
    ("in", "the", "comments"),
    ("let", "me", "know"),
    ("link", "in", "the"),
    ("in", "the", "description"),
    ("check", "out"),
    ("notification",),
    ("notifications",),
    ("patreon",),
    ("merch",),
)
