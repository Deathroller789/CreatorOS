"""Tests for the deterministic evidence-strength rubric.

Strength states *support*, never probability or truth. These tests pin both the
arithmetic and that boundary: nothing ever reaches "certain", and a finding the sample
cannot support is labelled weak however dramatic its numbers look.
"""

from __future__ import annotations

import unittest

from creatoros.intelligence import strength


class ComparisonStrengthTests(unittest.TestCase):
    def test_large_effect_on_a_real_sample_is_strong(self) -> None:
        self.assertEqual(strength.comparison_strength(0.9, 12, 12), strength.STRONG)

    def test_medium_effect_on_a_modest_sample_is_moderate(self) -> None:
        self.assertEqual(strength.comparison_strength(0.6, 6, 6), strength.MODERATE)

    def test_a_huge_effect_from_tiny_groups_is_still_weak(self) -> None:
        # The failure mode from issue #42: d=-3.45 from 2-vs-2 is noise wearing a
        # decimal point. Group size gates the label, not the magnitude alone.
        self.assertEqual(strength.comparison_strength(3.45, 2, 2), strength.WEAK)

    def test_a_withheld_effect_size_is_weak_not_generous(self) -> None:
        self.assertEqual(strength.comparison_strength(None, 20, 20), strength.WEAK)

    def test_the_smaller_group_decides(self) -> None:
        # 30 vs 3 is a 3-video comparison wearing a large n.
        self.assertEqual(strength.comparison_strength(0.9, 30, 3), strength.WEAK)

    def test_strength_never_reaches_certainty(self) -> None:
        labels = {
            strength.comparison_strength(d, n, n)
            for d in (0.0, 0.5, 0.9, 5.0)
            for n in (1, 5, 50)
        }
        self.assertTrue(labels <= {strength.WEAK, strength.MODERATE, strength.STRONG})


class NegligibleTests(unittest.TestCase):
    def test_a_tiny_standardised_difference_is_negligible(self) -> None:
        self.assertTrue(strength.is_negligible(0.05, 0.5))

    def test_a_real_effect_is_not_negligible(self) -> None:
        self.assertFalse(strength.is_negligible(0.6, 0.40))

    def test_a_respectable_effect_on_a_trivial_gap_is_still_negligible(self) -> None:
        # Titles of 40.6 vs 40.4 characters can post a solid d purely because every
        # title is nearly the same length. True, and useless to a creator (Part G).
        self.assertTrue(strength.is_negligible(0.6, 0.005))

    def test_without_an_effect_size_the_relative_difference_decides(self) -> None:
        self.assertTrue(strength.is_negligible(None, 0.02))  # 2% apart — noise
        self.assertFalse(strength.is_negligible(None, 0.50))  # 50% apart — real


class PhraseStrengthTests(unittest.TestCase):
    def test_widely_recurring_phrase_on_a_real_corpus_is_strong(self) -> None:
        self.assertEqual(strength.phrase_strength(10, 0.5, 20), strength.STRONG)

    def test_a_high_ratio_on_a_tiny_corpus_is_not_strong(self) -> None:
        # 2 of 3 videos is 67%, but three videos cannot establish a channel habit.
        self.assertNotEqual(strength.phrase_strength(2, 0.67, 3), strength.STRONG)

    def test_a_rare_phrase_is_weak(self) -> None:
        self.assertEqual(strength.phrase_strength(2, 0.04, 50), strength.WEAK)


if __name__ == "__main__":
    unittest.main()
