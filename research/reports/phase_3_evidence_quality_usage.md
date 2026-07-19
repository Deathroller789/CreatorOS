# Phase 3 usage: evidence quality across 25 channels

- **Date:** 2026-07-14
- **Scope:** the improved Evidence Engine run over every ingested channel, not a selection
- **Sample:** 25 channels across 8 niches, 25 videos each (MrBallen 53), ~600 videos

Not cherry-picked: every channel ingested for this sweep is reported below, including the
ones that produced nothing useful. Two channels failed to ingest at all
(`@PatrickBoyleOnFinance`, `@SmarterEveryDay` under one handle spelling) and are excluded
only because there is no data, not because the results were poor.

## Niches covered

education (5), technology (4), finance (3), storytelling (4), gaming (2), commentary (2),
documentary (2), news (2).

## What repeatedly appears useful

**Title structure evidence survives almost everywhere.** Across 25 channels, the title
family cleared filtering on: `title_length` (20 channels), `title_has_number` (18),
`title_caps_ratio` (18), `title_word_count` (16), `title_has_brackets` (13),
`title_has_question` (13). This is the most consistently informative evidence the engine
produces, and it needs no transcript.

**Narrative evidence is the most valuable when it exists.** Veritasium (the one channel
with full transcript coverage) produced the richest report in the sweep — 11 surviving
comparisons including *conflict language* 3.1 vs 2.1 per 1k words, *quoting people* 1.1 vs
2.0, *sequencing words* 11.1 vs 9.1, and *calls to action* 0.3 vs 0.6, all between its top
and bottom six videos. This is exactly the "why" evidence the engine exists to gather, and
none of it is available without captions.

**Recurring-phrase evidence is real but channel-dependent.** After tightening the support
floor, "words you reuse in titles" appears for 12 of 25 channels — the ones that genuinely
have a title formula (MrBallen's *stories* in 9 of 50; *campfire stories with*). The other
13 correctly say nothing, which is the honest result.

## What repeatedly appears useless

- **`callback_overlap`** cleared filtering on 2 channels, weak both times. It measures word
  reuse between a video's ends, and in practice that tracks topic vocabulary, not craft.
  The weakest metric added this milestone.
- **`curiosity_word_rate` and `authority_word_rate`** survived on one channel each, weak.
  Either the lexicons are too narrow or these registers do not vary within a channel.
- **`title_starts_with_number`** cleared on 5 channels; almost entirely subsumed by
  `title_has_number`, which is more often informative.
- **Whole-transcript "phrases you repeat"** is the most expensive family to compute and
  mostly surfaces sponsor/CTA boilerplate. Openings and endings carry the same signal for a
  fraction of the cost.

## What surprised us

**No finding on any of 25 channels reached "strong".** The strongest evidence the engine
produced anywhere is *moderate*. Title structure, narrative register, and phrasing all
accompany performance weakly at best. This is the single most important result of the
sweep, and it is an honest one (RFC-002: absence of convergence is not failure). It also
means the strength scale is doing real work — it is not a rubber stamp.

**Transcript availability, not analysis, is the binding constraint.** Only 6 of 25 channels
carry transcripts in this database, and only one carries full coverage. YouTube rate-limits
caption retrieval aggressively: a burst of requests returns a transient refusal that the
old pipeline recorded as "this video has no captions" — silently converting a rate limit
into a permanent-looking absence. That defect is fixed (transient failures are now retried
and reported as `blocked`), but the coverage it cost has to be refilled over time.

## What should probably be removed

`callback_overlap` and `title_starts_with_number` are candidates for removal if a second
sweep confirms them. Both are kept for now: one sweep at this transcript coverage is not
enough evidence to delete evidence.

## Part C: how the two performance groups should be formed

The question was whether comparing the **top and bottom quartiles** beats comparing
**above- vs below-baseline**. Both strategies were run over identical data for every
channel:

| Grouping | mean \|d\| | comparisons/channel | non-weak findings/channel |
|----------|-----------|---------------------|---------------------------|
| Top/bottom quartile | **0.659** | 5.1 | **3.33** |
| Above/below baseline | 0.516 | 4.9 | 1.83 |

Quantile grouping separates the groups 28% more sharply and yields 82% more findings that
clear the strength bar, without surfacing more rows overall — it is better evidence, not
more evidence. **Adopted**, with a fallback to the baseline split below 12 videos, where a
quarter would be one or two videos per side.

## Architecture review (Part I)

Two points of friction, both resolved inside the existing layers:

1. **Optional raw fields.** A metric depending on a column that only some records carry
   (`transcript_text`, `duration`) forced every fixture and loader to supply the key. The
   engine now treats a field absent from *every* record as a typo (loud failure) and a
   field absent from *this* record as missing data (propagates `None`). The typo guard is
   preserved; the friction is gone.
2. **Shared expensive derivations.** Roughly a dozen narrative signals each re-tokenised
   the full transcript, making metrics the slowest stage in the pipeline (10.6s for 25
   videos). The fix was already available in ADR-006: make tokenisation one metric and have
   the others *depend* on it. Metrics dropped to 1.4s and intelligence to 3.4s. The lesson
   is a design rule, not a new abstraction: **the dependency graph is the sharing
   mechanism; a metric that recomputes a shared derivation is a smell.** A test now asserts
   every narrative metric depends on `transcript_tokens`.

No new layer, no new abstraction, and no ADR was needed for either.

## What creators would actually value

Ranked by what this sweep showed the engine can actually support:

1. **"How you open and close"** — a creator's own recurring hook and sign-off, quoted back
   to them. Available wherever transcripts are.
2. **Title formula vs performance** — which structural title choices accompany the top
   videos, available everywhere.
3. **Narrative register differences** — conflict/sequencing/viewer-address rates between
   strong and weak videos. The most distinctive output, transcript-gated.

The honest caveat that must travel with all three: at this sample size the relationships
are moderate at best, and the report says so.
