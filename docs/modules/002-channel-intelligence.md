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
- **Every conclusion carries evidence, confidence, and sample size.** All three, every time,
  or it is not reported: the derived numbers behind the claim, a plain-language confidence
  qualifier tied to the effect and the sample, and the n it rests on. At n≈50 findings are
  suggestive, not proof — and the report says exactly that.
- **Prefer rankings to thresholds.** "These five sit furthest above baseline, by this much"
  is more honest at small n than a cutoff that manufactures a hard line the data does not
  have. Use a threshold only where a decision truly needs a binary, and state it.
- **Descriptive, never predictive.** "These over-performed and share these traits" — never
  "use this title." The module explains what happened; it does not promise outcomes.
- **Deterministic, read-only, no new dependencies, no LLM in v1.** Stdlib over SQLite. An
  LLM synthesis pass, if ever, is a later layer that reads these findings — it is
  intelligence, not a metric ([ADR-006](../decisions/adr-006-raw-derived-analysis.md)).
- **The module requests metrics; it never computes them.** Adding a metric must not require
  editing this module.

## Things Channel Intelligence must never do

Hard invariants. Unlike the non-goals below — features simply not in scope yet — these never
become acceptable. They are what keep the intelligence honest.

- **Never mutate data.** Strictly read-only. It never writes, updates, or deletes a raw row
  or a derived value; it reads the database and the metrics engine and emits a report.
  Nothing flows back.
- **Never state a conclusion without evidence, confidence, and sample size.** All three, or
  it is not reported. No bare assertion, no number without its n.
- **Never predict or prescribe.** It reports what happened, not what to do — never "use this
  title," "post on Tuesdays," or any promise of a future outcome.
- **Never compute a metric inline.** If a quantity is missing it becomes a metric in the
  engine ([ADR-006](../decisions/adr-006-raw-derived-analysis.md)), not a helper here.
- **Never derive from raw fields.** Analysis reads *derived* metrics only. The sole contact
  with raw data is passing rows *into* the engine; the module never does arithmetic on them.
- **Never invent a fact.** Every reported number is reproducible from stored data by the
  deterministic path. A later synthesis layer may phrase findings in prose, but it reads the
  facts — it never manufactures them.
- **Never treat rank as significance.** Being first in a ranking proves nothing on its own;
  every ranking travels with its effect size and sample size, so position is not mistaken for
  certainty.

## The questions

Six questions, grouped by theme. The examples in #13 and the
[product review](../../research/reports/next_milestone_product_review.md) map onto these.

### Performance

**Q1 — Which videos were true outliers, over and under?**

- *Means:* which videos beat, or missed, the channel's own age-normalized baseline by enough
  that it is unlikely to be noise — both tails, because underperformers are as informative as
  hits.
- *Honest answer:* videos **ranked** by `performance_index`, each shown as **expected**
  (`median_views_per_day × upload_age_days`) vs **actual** (raw views) vs **difference**
  ("3.4x baseline"), reporting both tails. Prefer the ranking to a hard outlier/not cutoff —
  at n≈50 the ranking carries the honest amount of information, where a threshold would
  invent a line the data does not have. Always with the sample size and a confidence
  qualifier.
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
- *Inputs:* `performance_index` (exists) **+ a topic assignment (new — see Q4/Q5).**
  **Deferred behind the topics RFC** ([#21](https://github.com/Deathroller789/CreatorOS/issues/21)).
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
  returning a table, or as a separate derived component, is exactly what the **topics RFC**
  ([#21](https://github.com/Deathroller789/CreatorOS/issues/21)) must decide. Deferred until
  it does.
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
  question here; **deferred behind the topics RFC**
  ([#21](https://github.com/Deathroller789/CreatorOS/issues/21)) with the rest of topic
  intelligence.
- *How it misleads:* lexical clusters overfit shared words and understand no meaning;
  single-video "clusters" mean nothing. Easy to oversell — so it is reported conservatively.

## Question → inputs map

| Question | Derived inputs | Status | Answer unit |
| --- | --- | --- | --- |
| Q1 Outliers (both tails) | `performance_index`, `views_per_day`, `median_views_per_day`, `upload_age_days` | **Ready now** | expected vs actual vs difference |
| Q3 Cadence | `upload_interval_days` | **1 new metric** | median gap, spread, trend |
| Q2 Title traits | `title_length`, `title_word_count` + `has_question_mark`, `caps_ratio`, `emoji_count`, `has_number` | **v1 — minimal now, deepens with [#19](https://github.com/Deathroller789/CreatorOS/issues/19)** | group difference + effect size + n |
| Q4 Topics | tokenization + stopwords + frequency | **Deferred — topics RFC [#21](https://github.com/Deathroller789/CreatorOS/issues/21)** | ranked terms + document frequency |
| Q5 Clusters | Q4 + lexical clustering | **Deferred — topics RFC [#21](https://github.com/Deathroller789/CreatorOS/issues/21)** | clusters with size + top terms |
| Q6 Topic-conditioned underperformers | `performance_index` + topic assignment | **Deferred — topics RFC [#21](https://github.com/Deathroller789/CreatorOS/issues/21)** | under-baseline within a topic |

## Recommendation

Build in the order the inputs are ready, so the first slice is honest and small.

- **v1 — the first shippable insight report:** **Q1** (outliers, served entirely by existing
  metrics), **Q2** (title characteristics), and **Q3** (cadence, one new `upload_interval_days`
  metric). Q2 ships minimally on the two title metrics that exist today (`title_length`,
  `title_word_count`) and deepens as the roadmap features in
  [#19](https://github.com/Deathroller789/CreatorOS/issues/19) land — the analysis code does
  not change when a feature is added, which is the point of the engine.
- **Deferred — all topic intelligence (Q4, Q5, Q6).** None of it enters the module until an
  **RFC defines how topics are represented** ([#21](https://github.com/Deathroller789/CreatorOS/issues/21)).
  Nothing that depends on topic extraction ships before that decision is made.

Every metric v1 surfaces (`upload_interval_days`, the [#19](https://github.com/Deathroller789/CreatorOS/issues/19)
title features) is **additive to the engine** and, by
[ADR-006](../decisions/adr-006-raw-derived-analysis.md), changes nothing in this module. That
is the drift protection working as designed.

Confidence: **High** that Q1 + Q2 + Q3 are the right v1 and that existing metrics already
answer Q1. **Medium** on how much title signal a single channel's ~50 videos holds — which
the report will reveal honestly rather than hide.

## Open questions

- **Command name.** `analyze-channel` is ingestion. The intelligence command is unnamed;
  candidates include `analyze-patterns`, `channel-report`, `channel-intelligence`. Align with
  the [vision command list](../ENGINEERING.md) when chosen.
- **Report location.** Alongside channel reports in `output/reports/`, or a separate
  `output/insights/`?

Two earlier open questions are now settled. **Outlier presentation** is a **ranking**, not a
threshold (see the rules) — a cutoff is added only if a later consumer needs a binary.
**Topic representation** is escalated out of this document into its own **RFC**
([#21](https://github.com/Deathroller789/CreatorOS/issues/21)); it is the gate for Q4–Q6, not
a detail to settle inline.

## Non-goals

Scope not yet in the module — deferred, not forbidden (contrast the invariants above).

- **All topic intelligence (Q4–Q6)** — gated behind the topics RFC
  ([#21](https://github.com/Deathroller789/CreatorOS/issues/21)).
- **No LLM and no new dependencies in v1.** A later synthesis layer may turn these findings
  into prose (Anthropic SDK direct, per the [reuse audit](../../research/technology/reuse_audit.md))
  — it reads the facts, it does not replace them.
- **No comment data** — deferred ([#2](https://github.com/Deathroller789/CreatorOS/issues/2)).
- **No cross-channel comparison** — Sprint 4+ (`compare-channels`, `discover-topic-gaps`),
  reachable only because these per-channel primitives come first.

## Next actions

- **Write the topics RFC** ([#21](https://github.com/Deathroller789/CreatorOS/issues/21)) —
  how topics are represented: the term-frequency table fits neither engine scalar shape
  (metric-that-returns-a-structure vs a separate derived component), plus tokenization,
  stopwords, and title-vs-transcript weighting. It gates Q4–Q6.
- File `upload_interval_days` (Q3) as an additive engine metric; the Q2 title features are
  already tracked in [#19](https://github.com/Deathroller789/CreatorOS/issues/19).
- Once this design is accepted, open the v1 implementation issue against #13 scoped to **Q1 +
  Q2 + Q3** — read-only, no new dependencies, emitting one markdown insight report.
