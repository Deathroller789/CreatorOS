# ADR-006: Raw → Derived → Analysis (the Derived Metrics Engine)

- **Status:** Accepted
- **Date:** 2026-07-10

## Context

Sprint 2 shipped ingestion: raw channel, video, and transcript rows in SQLite. Sprint 3
adds the first intelligence module ([#13](https://github.com/Deathroller789/CreatorOS/issues/13)),
which needs quantities that do not exist in the raw data — age-normalized reach, a channel
baseline, how far a video sits above that baseline.

The naive path is for the intelligence module to compute those inline, straight from raw
columns. That fails in a specific and predictable way: every new metric becomes an edit to
the analysis code, two modules drift into two definitions of "views per day", and no metric
is testable without dragging analysis along with it. Raw view counts are also not
comparable to each other at all — a video published two years ago has had two years to
accumulate them.

## Decision

Interpose a **derived-metrics layer** between ingestion and analysis:

```
Raw (SQLite)  ->  Derived (creatoros/metrics/)  ->  Analysis (intelligence module)
```

The layer is a small engine with a registry. A metric is a **pure function** that declares
its `scope`, its `unit`, and the names it `depends_on`. The engine owns everything else.

- **Metrics are pure.** They receive plain values and return a value. No I/O.
- **Metrics never access SQLite.** Nothing in `creatoros/metrics/` imports `sqlite3`; a test
  asserts this.
- **Metrics declare dependencies** by name. A dependency is either another registered metric
  or a raw field on the record. The engine resolves which, topologically orders the graph,
  and rejects cycles.
- **Metrics declare units** (`days`, `views/day`, `ratio`, `characters`, `words`), so a
  report can label a number without guessing what it means.
- **Metrics are discovered automatically.** Importing `creatoros.metrics` imports every
  module in the package, and each decorated function registers itself.
- **Metrics compose.** `performance_index` depends on `views_per_day` and
  `median_views_per_day`; it does not recompute either.
- **The analysis layer only requests metrics.** It calls `compute(...)` and reads values. It
  never computes one, and never derives anything from a raw field.

**Computed on read, not materialized.** `compute()` evaluates in memory from raw rows. There
is no `video_metrics` table.

**Missing data propagates.** If a scalar dependency is `None`, the metric is `None` and the
function is never called. Metric authors write the happy path. A channel metric aggregating
a video metric receives the sample as a series with the undefined entries dropped, so one
video with hidden view counts cannot poison the channel baseline.

**`now` is injected**, not read from the clock inside a metric. That is what keeps
age-normalized metrics pure and their tests deterministic.

## Alternatives

- **Helper functions in a `metrics/` folder.** Simplest thing that could work, and the
  original shape of [#14](https://github.com/Deathroller789/CreatorOS/issues/14). Rejected:
  it gives no ordering, no composition, and nothing stops a helper from opening the
  database or an analysis module from computing a ratio inline. The rule would live in a
  document instead of in the code.
- **Materialize into a `video_metrics` table.** Rejected *for now*: it adds a schema
  migration and a staleness problem — a video's view count changes on every re-ingest, so
  every derived row would need invalidating. At 50 videos per channel the computation is
  microseconds. Revisit when a metric becomes genuinely expensive (an embedding, an LLM
  call) or when metrics need to be queried across channels in SQL.
- **A dataframe library (pandas / DuckDB).** Rejected: a dependency for arithmetic we can
  do in the standard library, against samples of tens of rows. Already deferred in the
  [reuse audit](../../research/technology/reuse_audit.md).

## Tradeoffs

- **Gain:** adding a metric is one decorated function in one file. The intelligence module
  does not change, the engine does not change, and the metric is unit-testable in isolation.
  The Raw → Derived → Analysis boundary is enforced by code and by a test, not by discipline.
- **Give up:** a small amount of indirection. Reading `performance_index` means reading the
  function *and* knowing the engine supplies its arguments by name. Dependency names are
  strings, so a typo is caught at import (parameters must match `depends_on` exactly) rather
  than by a type checker.
- **Give up:** recomputation. Every `compute()` re-derives from raw. This is the right trade
  at our sample sizes and the wrong one at a million rows.

## Consequences

- `creatoros/metrics/` is the only place a derived quantity is defined. The intelligence
  module ([#13](https://github.com/Deathroller789/CreatorOS/issues/13)) consumes it and is
  forbidden from touching raw fields to derive anything.
- The baseline is the **median**, never the mean: one viral video must not redefine what
  normal looks like for a channel.
- `performance_index` is the unit in which over-performance is reported — "2.7x baseline",
  expected vs actual vs difference — never a raw "top video" ranking.
- Metrics deferred to later, with no code today: `caps_ratio`, `question_mark`,
  `emoji_count`, `word_count`, and `momentum_score`
  ([#15](https://github.com/Deathroller789/CreatorOS/issues/15)). Each is additive.
- **Revisit trigger:** the first metric that is too slow to recompute on every read, or the
  first need to query derived values in SQL across channels. Then materialize — the metric
  functions themselves would not change, only where the engine puts their output.
- Reading raw rows out of SQLite stays outside this layer for now. The intelligence module
  loads them and hands them in. If a second consumer appears, that loader moves into
  `creatoros/metrics/` as its single I/O boundary.

## Exit strategy

**Trivial.** Standard library only — no dependency is being adopted. The engine is roughly
150 lines and the metrics are pure functions of plain values. If the registry ever stops
paying for itself, each metric can be called directly as an ordinary function, and the
engine deleted, without touching the metric bodies. The canonical data remains the raw
SQLite tables, which this layer never writes to.
