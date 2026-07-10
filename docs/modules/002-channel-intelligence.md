# Module 002: Channel Intelligence — What it answers

_System design document. No implementation code. Defines the **product questions** the
Channel Intelligence module ([#13](https://github.com/Deathroller789/CreatorOS/issues/13))
must answer, before any of them is built, so the implementation follows the questions
instead of drifting toward whatever the metrics happen to make easy. The module consumes
**derived metrics** ([ADR-006](../decisions/adr-006-raw-derived-analysis.md)); it never
reads raw fields and never computes a metric inline._

## Why questions before metrics

The metrics engine is a means, not the point. The product exists to answer questions about
a channel — "which videos were true outliers?", "is the upload cadence consistent?" — and
the metrics exist only to answer them. Define the questions first and the implementation is
constrained and obvious. Define the metrics first and the module drifts toward reporting
whatever is cheap to compute, which is how analytics tools end up with fifty numbers and no
answers.

So this document lists the questions. For each: what it means, what an **honest** answer
looks like, which derived inputs it needs (and whether they exist yet), and how the answer
could mislead. The metric gaps this surfaces are the real backlog — not guessed at, but
derived from the questions that need them.

## The rules every answer obeys

These are not per-question; they hold for the whole module. They come from
[ENGINEERING.md](../ENGINEERING.md), [ADR-006](../decisions/adr-006-raw-derived-analysis.md),
and the [product review](../../research/reports/next_milestone_product_review.md).

- **Age-normalize everything.** A 2-day-old video and a 2-year-old video are never compared
  on raw views. Reach is `views_per_day`; standing is `performance_index`.
- **The baseline is the channel median, never the mean.** One viral video must not redefine
  what normal looks like.
- **Top Outlier, not "top video."** Report **expected vs actual vs difference**, e.g. "2.7x
  baseline", not a raw leaderboard.
- **Report effect size *and* sample size, every time.** At n≈50 (and far less per topic),
  findings are suggestive, not proof. The report says so.
- **Descriptive, never predictive.** "These over-performed and share these traits" — never
  "use this title." The module explains what happened; it does not promise outcomes.
- **Deterministic, read-only, no new dependencies, no LLM in v1.** Stdlib over SQLite. An
  LLM synthesis pass, if ever, is a later layer that reads these findings — it is
  intelligence, not a metric ([ADR-006](../decisions/adr-006-raw-derived-analysis.md)).
- **The module requests metrics; it never computes them.** Adding a metric must not require
  editing this module.

## The questions

Six questions, grouped by theme. The examples in #13 and the
[product review](../../research/reports/next_milestone_product_review.md) map onto these.

### Performance

**Q1 — Which videos were true outliers, over and under?**

- *Means:* which videos beat, or missed, the channel's own age-normalized baseline by enough
  that it is unlikely to be noise — both tails, because underperformers are as informative as
  hits.
- *Honest answer:* per outlier, **expected** (`median_views_per_day × upload_age_days`) vs
  **actual** (raw views) vs **difference**, plus `performance_index` ("3.4x baseline"). A
  "true" outlier clears a **threshold**, not merely the top of a sorted list — see Open
  Questions. Always with the sample size.
- *Inputs:* `performance_index`, `views_per_day`, `median_views_per_day`, `upload_age_days`
  — **all exist today.**
- *How it misleads:* a very fresh video can post a huge `views_per_day` spike that will not
  hold — flag recency. Deleted flops are absent (survivorship). At small n, three "outliers"
  may be chance.

**Q6 — Which videos underperformed despite similar topics?**

- *Means:* Q1 conditioned on topic — same subject, worse outcome. The most actionable
  descriptive finding, because it isolates packaging/timing from topic.
- *Honest answer:* within a topic group (Q4/Q5), the videos with `performance_index < 1`,
  reported with the group's size. Only stated where the group is large enough to mean
  anything.
- *Inputs:* `performance_index` (exists) **+ a topic assignment (new — see Q4/Q5).** Depends
  on topics being solid, so this is **v2.**
- *How it misleads:* tiny per-topic n; "topic" can smuggle in format or length differences.

### Titles

**Q2 — Which title characteristics recur in above-baseline videos?**

- *Means:* do above-baseline videos share measurable title traits (length, a number, a
  question, casing) that below-baseline videos lack?
- *Honest answer:* split the sample into above- vs below-baseline groups, and for each title
  feature report the **difference between groups with an effect size and both group sizes** —
  "above-baseline titles average 6.2 words (n=18) vs 8.9 (n=27)." Never "use short titles."
  Testing many features at once inflates false positives; the report flags the
  multiple-comparison caveat.
- *Inputs:* `title_length`, `title_word_count` (exist); `has_question_mark`, `caps_ratio`,
  `emoji_count`, `has_number`, `has_colon` (**roadmap
  [#19](https://github.com/Deathroller789/CreatorOS/issues/19)** — this question is the
  concrete reason those metrics exist).
- *How it misleads:* correlation is not causation; confounds (topic, video length); small
  groups swing easily.

### Cadence

**Q3 — Is upload cadence consistent?**

- *Means:* how regularly does the channel publish, and is the rhythm steady, accelerating, or
  slowing across the sampled window?
- *Honest answer:* from upload dates, the **inter-upload interval** distribution — median
  gap, spread (IQR or coefficient of variation), longest gap, and direction of change.
  Descriptive.
- *Inputs:* a **new derived metric**, `upload_interval_days` (channel-scope, a series over
  chronologically sorted uploads), built from raw `upload_date`. `upload_age_days` exists but
  is not the same thing.
- *How it misleads:* the sample is the *latest* N uploads, so it describes **recent** cadence,
  not lifetime; the boundary gap is truncated; Shorts and long-form may run different rhythms.

### Topics

**Q4 — Which topics dominate this channel?**

- *Means:* what subjects recur across the catalog, by the channel's own words.
- *Honest answer:* term and phrase **frequency** across titles and transcripts, via stdlib
  tokenization and a stopword list, reported as top terms with counts **and document
  frequency** (in how many videos). Descriptive.
- *Inputs:* **new** — tokenization, stopwords, frequency counting. Note the shape mismatch:
  the engine produces one scalar per record, and a term-frequency table is neither
  per-video nor a scalar. Whether this lives *in* the engine as a channel-scope metric
  returning a table, or as a separate derived component the module builds, is a real design
  question — see Open Questions.
- *How it misleads:* raw frequency is not importance; transcripts outweigh titles by volume;
  stopword quality and casing/stemming decisions change the answer; a brand name trivially
  tops every list.

**Q5 — Are there identifiable content clusters?**

- *Means:* do the videos fall into a few recognizable content groups?
- *Honest answer:* group videos by shared vocabulary using **stdlib only** (keyword overlap
  or TF-IDF with a simple similarity threshold), reporting each cluster's **size** and top
  terms, and stating plainly that the grouping is lexical, not semantic. Embeddings/vector
  search are deferred ([Chroma evaluation](../../research/technology/chroma.md)).
- *Inputs:* builds on Q4 tokenization **+ new clustering logic.** The most speculative
  question here; a lightweight version, or deferral to **v2**, is likely.
- *How it misleads:* lexical clusters overfit shared words and understand no meaning;
  single-video "clusters" mean nothing. Easy to oversell — so it is reported conservatively.

## Question → inputs map

| Question | Derived inputs | Status | Answer unit |
| --- | --- | --- | --- |
| Q1 Outliers (both tails) | `performance_index`, `views_per_day`, `median_views_per_day`, `upload_age_days` | **Ready now** | expected vs actual vs difference |
| Q3 Cadence | `upload_interval_days` | **1 new metric** | median gap, spread, trend |
| Q2 Title traits | `title_length`, `title_word_count` + `has_question_mark`, `caps_ratio`, `emoji_count`, `has_number` | **Roadmap [#19](https://github.com/Deathroller789/CreatorOS/issues/19)** | group difference + effect size + n |
| Q4 Topics | tokenization + stopwords + frequency | **New (shape TBD)** | ranked terms + document frequency |
| Q5 Clusters | Q4 + lexical clustering | **New / v2** | clusters with size + top terms |
| Q6 Topic-conditioned underperformers | `performance_index` + topic assignment | **Depends on Q4/Q5 → v2** | under-baseline within a topic |

## Recommendation

Build in the order the inputs are ready, so the first slice is honest and small.

- **v1 — the first shippable insight report:** **Q1** (fully served by existing metrics —
  the natural first cut), **Q3** (one new `upload_interval_days` metric), and **Q4** at the
  frequency level (tokenization + stopwords). Add **Q2** once the roadmap title metrics from
  [#19](https://github.com/Deathroller789/CreatorOS/issues/19) land — the analysis code is
  the same regardless of how many title features exist, which is the point of the engine.
- **v2:** **Q5** (clustering) and **Q6** (topic-conditioned underperformers), once topic
  extraction is trustworthy.

Every new metric this surfaces (`upload_interval_days`, the Q2 title features, the topic
machinery) is **additive to the engine** and, by [ADR-006](../decisions/adr-006-raw-derived-analysis.md),
changes nothing in this module. That is the drift protection working as designed.

Confidence: **High** that Q1/Q3/Q4 are the right v1 and that the existing metrics already
answer Q1. **Medium** on how much signal a single channel's ~50 videos holds for Q2 — which
the report will reveal honestly rather than hide.

## Open questions

- **Is topic frequency a metric or a component?** The engine returns a scalar per record; a
  term-frequency table fits neither the video nor the channel scalar shape. Extend the engine
  to allow a channel-scope metric that returns a structure, or build topic extraction as a
  separate derived component beside the engine? This is the one architectural decision this
  design forces, and it deserves its own ADR before Q4 is built.
- **Outlier threshold (Q1).** What makes a "true" outlier at n≈50 — a fixed multiple of
  baseline (e.g. `performance_index ≥ 2`), or a spread-based rule (distance from the median in
  median-absolute-deviations)? Pick one and state it in the report.
- **How much of Q5 to attempt in v1** without embeddings — a crude lexical pass, or defer
  entirely.
- **Command name.** `analyze-channel` is ingestion. The intelligence command is unnamed;
  candidates include `analyze-patterns`, `channel-report`, `channel-intelligence`. Align with
  the [vision command list](../ENGINEERING.md) when chosen.
- **Report location.** Alongside channel reports in `output/reports/`, or a separate
  `output/insights/`?

## Non-goals

- No predictions, no recommendations, no "you should" — descriptive only.
- No LLM in v1; no new dependencies; no comment data (deferred, #2).
- No cross-channel comparison — that is Sprint 4+ (`compare-channels`,
  `discover-topic-gaps`), reachable only because these per-channel primitives come first.
- The module never computes a metric inline. If a number is missing, it becomes a metric in
  the engine, not a helper here.

## Next actions

- Decide the **topic-shape** open question (metric vs component) and write its ADR — it
  blocks Q4/Q5/Q6.
- File the metrics this surfaces as additive to the engine: `upload_interval_days` (Q3) now;
  the Q2 title features are already tracked in
  [#19](https://github.com/Deathroller789/CreatorOS/issues/19).
- Once this design is accepted, open the v1 implementation issue against #13 scoped to **Q1 +
  Q3 + Q4**, infrastructure-free and read-only, emitting one markdown insight report.
