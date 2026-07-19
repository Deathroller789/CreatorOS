"""Tests for the deterministic text primitives behind corpus evidence.

Each normalisation exists to make genuinely-recurring language *look* recurring. These
tests pin the behaviour that phrase quality depends on, so a future change to one rule
cannot quietly degrade the evidence.
"""

from __future__ import annotations

import unittest

from creatoros.metrics.text import (
    NUMBER_PLACEHOLDER,
    clean_text,
    is_content_word,
    is_stopword,
    normalize_key,
    tokenize,
)


class CleanTextTests(unittest.TestCase):
    def test_caption_annotations_are_removed(self) -> None:
        # "[Music]" is not the creator's language; left in, every video "says" it and it
        # dominates the recurring-phrase counts.
        self.assertEqual(
            clean_text("[Music] hello (upbeat music) world"), "hello world"
        )

    def test_speaker_markers_are_removed(self) -> None:
        self.assertEqual(clean_text(">> JOHN: hello"), "JOHN: hello")

    def test_whitespace_is_collapsed(self) -> None:
        self.assertEqual(clean_text("a\n\n  b\tc"), "a b c")

    def test_blank_input_is_empty(self) -> None:
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text("   "), "")


class TokenizeTests(unittest.TestCase):
    def test_lowercases_and_splits_on_punctuation(self) -> None:
        self.assertEqual(tokenize("Hello, WORLD!"), ["hello", "world"])

    def test_contractions_stay_one_token(self) -> None:
        # Splitting on the apostrophe would fragment n-grams into "i m going".
        self.assertEqual(tokenize("I'm going"), ["im", "going"])

    def test_expanded_contractions_normalise_to_one_spelling(self) -> None:
        # A human caption track writes "do not"; an auto track writes "don't". The same
        # spoken words must produce the same tokens or the phrase never looks recurring.
        self.assertEqual(tokenize("do not"), tokenize("don't"))
        self.assertEqual(tokenize("I am here"), tokenize("I'm here"))

    def test_numbers_collapse_to_a_placeholder(self) -> None:
        # "Top 5 stories" and "Top 10 stories" are the same recurring format.
        self.assertEqual(
            tokenize("Top 5 stories"), ["top", NUMBER_PLACEHOLDER, "stories"]
        )
        self.assertEqual(tokenize("Top 5 stories"), tokenize("Top 10 stories"))

    def test_ordinals_collapse_too(self) -> None:
        self.assertEqual(tokenize("the 3rd time"), ["the", NUMBER_PLACEHOLDER, "time"])

    def test_speech_fillers_are_dropped(self) -> None:
        # Auto-captions transcribe "uh" literally; it is not language a creator chose.
        self.assertEqual(tokenize("so uh yeah um right"), ["so", "yeah", "right"])

    def test_blank_input_yields_no_tokens(self) -> None:
        self.assertEqual(tokenize(None), [])
        self.assertEqual(tokenize(""), [])


class NormalizeKeyTests(unittest.TestCase):
    def test_plurals_group_with_their_singular(self) -> None:
        self.assertEqual(normalize_key("stories"), normalize_key("story"))
        self.assertEqual(normalize_key("tricks"), normalize_key("trick"))

    def test_short_words_are_left_alone(self) -> None:
        # Over-stemming destroys more evidence than it merges.
        for word in ("this", "is", "us", "his"):
            with self.subTest(word=word):
                self.assertEqual(normalize_key(word), word)

    def test_double_s_and_us_endings_are_left_alone(self) -> None:
        self.assertEqual(normalize_key("class"), "class")
        self.assertEqual(normalize_key("virus"), "virus")

    def test_placeholder_is_untouched(self) -> None:
        self.assertEqual(normalize_key(NUMBER_PLACEHOLDER), NUMBER_PLACEHOLDER)


class StopwordTests(unittest.TestCase):
    def test_question_words_are_not_stopwords(self) -> None:
        # "how to", "why you", "what happens" are exactly the hooks we want to surface.
        for word in ("how", "why", "what", "when", "who", "which"):
            with self.subTest(word=word):
                self.assertFalse(is_stopword(word))

    def test_discourse_fillers_are_stopwords(self) -> None:
        # Common enough in speech to outrank every genuine phrase if left in.
        for word in ("like", "just", "actually", "really"):
            with self.subTest(word=word):
                self.assertTrue(is_stopword(word))

    def test_pronoun_contractions_are_stopwords(self) -> None:
        for word in ("im", "youre", "theyre", "thats"):
            with self.subTest(word=word):
                self.assertTrue(is_stopword(word))

    def test_content_words_need_length_and_meaning(self) -> None:
        self.assertTrue(is_content_word("mystery"))
        self.assertFalse(is_content_word("the"))  # stop word
        self.assertFalse(is_content_word("ab"))  # too short


if __name__ == "__main__":
    unittest.main()
