# Product Review — What Should CreatorOS Build Next?

## Summary

**Reviewed 2026-07-10.** Question: does another ingestion feature (#2, comments) produce
more user value than the first intelligence feature?

**Recommendation: No. Pause ingestion breadth. Build the first intelligence module.**
Sprint 3 should ship `creatoros analyze-patterns <channel>` — a deterministic, read-only
analysis over the SQLite data we already have, with **zero new dependencies**.

Two corrections that materially change the plan, and that a "just build the intelligence
module" answer would miss:

1. **Our sample is 5 videos per channel.** Any title/word/performance correlation over
   n=5 is noise. Raising the per-channel video limit is a *parameter change to existing
   ingestion* (not new ingestion breadth) and is a **precondition**, not a new feature.
2. **Raw view counts are confounded by video age.** A 2-day-old video and a 2-year-old
   video are not comparable. The module must normalize (views per day, and/or ratio to the
   channel's own baseline) or every conclusion it produces will be wrong.

Confidence: **High** on the direction; **High** on both corrections.

## Evidence

### What CreatorOS can already answer

Per channel we persist: title, description, upload date, duration, view/like/comment
counts, and full transcripts. That is enough to compute, with plain Python and SQL:

- **Performance outliers** — which videos beat the channel's own baseline (age-normalized).
- **Title structure** — length, presence of numbers, questions, colons, capitalization;
  which structures co-occur with over-performance.
- **Topic frequency** — dominant terms across titles/transcripts (stdlib tokenization +
  a stopword list; no NLP dependency).
- **Upload cadence** — gaps between uploads, day-of-week, and their relation to performance.

None of this needs an LLM. Per ENGINEERING.md principle 3, the statistics are deterministic
software; an LLM is only warranted later, to *synthesize* the findings into prose.

### Why comments (#2) lose on value

- Comments are **demand-side** signal ("what the audience asks for"). They do **not** answer
  the question the product exists to answer: *what already works*.
- They are, by our own [library evaluation](../technology/youtube_library_evaluation.md),
  the **most fragile and highest-volume** YouTube data — the worst effort-to-insight ratio
  of anything available to us.
- Their natural home is a later **topic-gap / audience-demand** module, once we can already
  characterize what performs. Collecting them now buys nothing we can act on.

### The trap being avoided

Data collection has unbounded depth: comments, community posts, Shorts, playlists, tags,
chapters, sponsors. Each feels like "one more thing," and none of them cross the threshold
from *collector* to *research assistant*. Intelligence is where value begins, and the
cheapest possible intelligence module beats the most complete possible dataset.

### Honest limits of the recommendation

- **Single-channel scope.** `analyze-patterns` tells you what works *for that channel*. The
  product goal ("discover winning YouTube ideas") ultimately needs **cross-channel**
  comparison (`compare-channels`, `discover-topic-gaps`). That is Sprint 4+, and it is
  reachable only because we will already have the per-channel primitives.
- **n=5 → n≈50.** With the limit raised, correlations become suggestive (not proof). We
  should report effect sizes and sample size honestly in the output, never as certainty.
- The first module's value is *descriptive*, not predictive. It should say "these titles
  over-performed and share these traits," not "use this title."

## Confidence

**High.** The direction follows from the product goal, and both corrections are mechanical
facts (sample size, age confounding) rather than judgments. The main uncertainty is how
much signal exists in a single channel's ~50 videos — which the module itself will reveal,
cheaply, and which is exactly why we should build it before collecting anything more.

## Sources

- `docs/PROJECT_VISION.md` (mission: compounding knowledge, intelligence layer)
- `docs/ENGINEERING.md` principles 1 & 3 (build only intelligence; don't ask an LLM what
  Python/SQLite can answer)
- [`research/technology/reuse_audit.md`](../technology/reuse_audit.md) (no new deps needed)
- [`research/technology/youtube_library_evaluation.md`](../technology/youtube_library_evaluation.md)
  (comments = most fragile data)
- Current schema and data: `creatoros/analyze.py`, `database/creatoros.db`

## Open Questions

- Target sample size per channel: 50? 100? Full backfill? (Cost is time, not complexity.)
- Should `analyze-patterns` read only from SQLite, or offer `--refresh` to re-ingest first?
  Prefer read-only; keep ingestion and intelligence separate.
- Where do insight reports live — alongside channel reports in `output/reports/`?

## Next Actions

- **Defer #2 (comments)** to the backlog; it is not the next milestone.
- Raise/parameterize the per-channel video limit (`--limit`, default ~50) — a small change
  to existing ingestion, and a precondition for meaningful analysis.
- Ship **Sprint 3: `creatoros analyze-patterns <channel>`** — read SQLite, age-normalize
  performance, flag outliers, extract deterministic title features, compute topic frequency,
  correlate features with normalized performance, emit a markdown insight report. No LLM, no
  new dependencies in v1.
- Only after that, consider an LLM synthesis pass (Anthropic SDK direct, per the reuse
  audit) to turn the statistics into readable recommendations.
