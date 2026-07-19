"""Tests for deterministic narrative feature extraction.

These metrics count language; they never classify a video or judge a hook. The tests pin
that boundary as much as the arithmetic: a signal fires on the words that are there, and
a video without enough transcript yields ``None`` rather than a fabricated zero.

The metrics consume the shared ``transcript_tokens`` metric rather than raw text, so
tokenisation happens once per video; these tests supply tokens as the engine would.
"""

from __future__ import annotations

import unittest

from creatoros.metrics import narrative
from creatoros.metrics.text import tokenize

# Long enough to clear the minimum-words floor, so rates are actually computed.
_FILLER = " ".join(["the story continues"] * 20)


def _transcript(opening: str) -> str:
    return f"{opening} {_FILLER}"


def _tok(text: str | None) -> list[str] | None:
    """Tokens exactly as the ``transcript_tokens`` metric would produce them."""
    tokens = tokenize(text)
    return tokens or None


class OpeningStyleTests(unittest.TestCase):
    def test_question_opening_detected_by_punctuation(self) -> None:
        text = _transcript("What happens when a star dies?")
        self.assertEqual(narrative.opening_is_question(text, _tok(text)), 1)

    def test_question_opening_detected_without_punctuation(self) -> None:
        # Auto-generated caption tracks routinely carry no punctuation at all.
        text = _transcript("what happens when a star dies")
        self.assertEqual(narrative.opening_is_question(text, _tok(text)), 1)

    def test_statement_opening_is_not_a_question(self) -> None:
        text = _transcript("A star collapsed last night and nobody noticed it")
        self.assertEqual(narrative.opening_is_question(text, _tok(text)), 0)

    def test_command_opening_detected(self) -> None:
        yes = _transcript("Imagine a room")
        no = _transcript("A room existed")
        self.assertEqual(narrative.opening_is_command(_tok(yes)), 1)
        self.assertEqual(narrative.opening_is_command(_tok(no)), 0)

    def test_viewer_address_detected_in_the_opening(self) -> None:
        yes = _transcript("You have seen this")
        no = _transcript("Nobody had seen it")
        self.assertEqual(narrative.opening_addresses_viewer(_tok(yes)), 1)
        self.assertEqual(narrative.opening_addresses_viewer(_tok(no)), 0)


class RateTests(unittest.TestCase):
    def test_lexicon_rate_counts_per_thousand_words(self) -> None:
        # Exactly one lexicon hit in 100 tokens -> 10 per 1,000.
        text = "mystery " + " ".join(["word"] * 99)
        self.assertAlmostEqual(narrative.curiosity_word_rate(_tok(text)), 10.0)

    def test_rate_is_length_normalised(self) -> None:
        # The same language at twice the length must score the same, or the metric is
        # just re-measuring video length.
        short = " ".join(["mystery word"] * 50)
        long = " ".join(["mystery word"] * 100)
        self.assertAlmostEqual(
            narrative.curiosity_word_rate(_tok(short)),
            narrative.curiosity_word_rate(_tok(long)),
        )

    def test_cta_needs_a_phrase_not_a_bare_common_word(self) -> None:
        # "like" and "channel" are far too common in speech to count on their own.
        plain = " ".join(["i like this channel"] * 25)
        self.assertEqual(narrative.cta_rate(_tok(plain)), 0.0)
        asking = "please subscribe " + " ".join(["word"] * 98)
        self.assertGreater(narrative.cta_rate(_tok(asking)), 0.0)

    def test_speech_pace_uses_duration(self) -> None:
        text = " ".join(["word"] * 300)
        self.assertAlmostEqual(narrative.speech_pace(_tok(text), 60), 300.0)

    def test_speech_pace_is_none_without_duration(self) -> None:
        self.assertIsNone(narrative.speech_pace(_tok(" ".join(["word"] * 300)), None))


class CallbackTests(unittest.TestCase):
    def test_repeated_opening_language_at_the_end_scores_higher(self) -> None:
        body = " ".join(["middle filler content"] * 30)
        echoed = f"lighthouse keeper vanished {body} lighthouse keeper vanished"
        unrelated = (
            f"lighthouse keeper vanished {body} entirely different closing words"
        )
        self.assertGreater(
            narrative.callback_overlap(_tok(echoed)),
            narrative.callback_overlap(_tok(unrelated)),
        )


class AbsenceTests(unittest.TestCase):
    def test_no_transcript_yields_none_everywhere(self) -> None:
        # A video without a transcript contributes nothing; it never scores zero, which
        # would read as "this creator uses no curiosity language" (ADR-009).
        self.assertIsNone(narrative.curiosity_word_rate(None))
        self.assertIsNone(narrative.opening_is_question(None, None))
        self.assertIsNone(narrative.cta_rate(None))

    def test_a_transcript_fragment_is_not_enough(self) -> None:
        # A stub caption track would produce wild rates from a handful of words.
        self.assertIsNone(narrative.curiosity_word_rate(_tok("a mystery")))


class SharingTests(unittest.TestCase):
    def test_narrative_metrics_consume_the_shared_token_metric(self) -> None:
        # The performance guard: tokenising a long transcript is the pipeline's most
        # expensive step, so every narrative signal must depend on ``transcript_tokens``
        # rather than re-tokenising the raw text itself (ADR-006 dependency sharing).
        from creatoros.metrics import registry

        for name, m in registry().items():
            if m.category != "narrative":
                continue
            with self.subTest(metric=name):
                self.assertIn("transcript_tokens", m.depends_on)


if __name__ == "__main__":
    unittest.main()
