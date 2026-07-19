"""Evidence strength: how much support a finding actually has.

Strength is **not** confidence, and emphatically not probability. It answers one
question — *how much does the data behind this finding actually support it?* — from
quantities already measured: how many videos back it, how consistently, and how far
apart the groups are. Nothing is estimated, modelled, or inferred (RFC-002: evidence
is confidence-bounded; ADR-011: deterministic only).

Two things it deliberately does not do:

- It never rises to "certain". The top of the scale is "strong", meaning *well
  supported by this sample*, not *true*.
- It never combines into a channel-level score. Aggregating strengths into one number
  would manufacture a verdict the evidence cannot carry (RFC-002: convergence is
  earned between independent classes, not averaged).

The thresholds are fixed constants chosen once, so the same finding always earns the
same label — a creator comparing two reports is comparing like with like.
"""

from __future__ import annotations

WEAK = "weak"
MODERATE = "moderate"
STRONG = "strong"

# Ranking for sorting and filtering (higher is stronger).
ORDER = {WEAK: 0, MODERATE: 1, STRONG: 2}

# Standardised mean difference (Cohen's d) bands. 0.2/0.5/0.8 are the conventional
# small/medium/large boundaries; below the negligible line a difference is not worth a
# creator's attention even when it is real.
NEGLIGIBLE_D = 0.2
MODERATE_D = 0.5
STRONG_D = 0.8

# How far apart the group means must be, relative to their own magnitude, before a
# difference is worth a creator's attention at all. Guards against a scale-free effect
# size dressing up a difference nobody could act on.
PRACTICAL_RELATIVE_FLOOR = 0.05
# When no effect size can be estimated, the practical bar is the only one left, so it
# is set higher.
NO_EFFECT_RELATIVE_FLOOR = 0.10

# Group sizes below which a separation cannot be called well-supported however large it
# looks — the instinct that withholds the effect size entirely under n=5 (issue #42).
MODERATE_GROUP_N = 5
STRONG_GROUP_N = 10

# Recurrence bands for corpus phrases: how many videos share the phrase, and what share
# of the contributing corpus that is. A phrase in 2 of 3 videos is a high *ratio* on a
# tiny base, so both a floor on the count and a floor on the ratio must be cleared.
MODERATE_PHRASE_COUNT = 3
STRONG_PHRASE_COUNT = 5
MODERATE_PHRASE_RATIO = 0.20
STRONG_PHRASE_RATIO = 0.40
STRONG_PHRASE_BASIS = 10


def comparison_strength(effect_size: float | None, above_n: int, below_n: int) -> str:
    """Strength of a between-group comparison, from its effect size and group sizes.

    ``effect_size`` is ``None`` when groups were too small to estimate it (issue #42);
    that is itself a statement of weak support, so it maps to ``weak`` rather than being
    given the benefit of the doubt.
    """
    smallest = min(above_n, below_n)
    if effect_size is None:
        return WEAK
    magnitude = abs(effect_size)
    if smallest >= STRONG_GROUP_N and magnitude >= STRONG_D:
        return STRONG
    if smallest >= MODERATE_GROUP_N and magnitude >= MODERATE_D:
        return MODERATE
    return WEAK


def is_negligible(effect_size: float | None, relative_difference: float) -> bool:
    """Whether a comparison is too small to be worth reporting at all.

    A comparison must clear *both* bars. The standardised effect says whether the groups
    separate relative to their own spread; the relative difference says whether the gap
    is big enough to matter in the real world. Either alone misleads:

    - Effect size is scale-free, so titles averaging 40.6 vs 40.4 characters can post a
      respectable ``d`` purely because every title is nearly the same length. True, and
      useless to a creator.
    - Relative difference alone would promote a large but wildly inconsistent gap.

    With no effect size (groups too small to estimate one), only the practical bar is
    available, so it is set higher.
    """
    relative = abs(relative_difference)
    if effect_size is None:
        return relative < NO_EFFECT_RELATIVE_FLOOR
    return abs(effect_size) < NEGLIGIBLE_D or relative < PRACTICAL_RELATIVE_FLOOR


def phrase_strength(document_count: int, document_ratio: float, basis_n: int) -> str:
    """Strength of a recurring phrase, from how widely it actually recurs."""
    if (
        basis_n >= STRONG_PHRASE_BASIS
        and document_count >= STRONG_PHRASE_COUNT
        and document_ratio >= STRONG_PHRASE_RATIO
    ):
        return STRONG
    if (
        document_count >= MODERATE_PHRASE_COUNT
        and document_ratio >= MODERATE_PHRASE_RATIO
    ):
        return MODERATE
    return WEAK
