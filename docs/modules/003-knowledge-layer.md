# Module 003: The Knowledge Layer — CreatorOS's memory

_System design document. No implementation code. Defines the responsibilities, inputs,
outputs, permanence, and relationships of the Knowledge layer — the last layer in the
architecture (Raw → Metrics → Intelligence → Reporting → Knowledge) and the one that makes
CreatorOS an operating system with a memory rather than a one-shot analyzer. It consumes
the **canonical findings** contract ([`ChannelFindings`](../../creatoros/intelligence/findings.py));
it never reads raw rows, never computes a metric, and never parses a rendered report._

## Why a knowledge layer

Everything below Knowledge is stateless in time. Ask CreatorOS about a channel today and it
ingests the current data, computes metrics, and produces a findings snapshot describing the
channel **as it is now**. Ask again in three months and you get a different snapshot — the
view counts grew, videos were added, the baseline moved. The two snapshots are both true,
and the difference between them is often the most valuable thing there is: _is the cadence
steadying? did the title strategy that emerged last quarter persist? is this month's outlier
part of a trend or a blip?_

None of that is answerable from a single snapshot, and none of it can be reconstructed
later, because **a past snapshot cannot be recomputed** — the data it described no longer
exists in that state. The Knowledge layer exists to hold those snapshots permanently and to
turn the series into longitudinal knowledge. It is where the principle "findings are
permanent, reports are disposable" stops being an aspiration and becomes a stored fact.

## Responsibilities

1. **Persist canonical findings, append-only.** Every findings snapshot produced by the
   intelligence layer, stamped with its provenance (when it was generated, against how many
   videos, under which engine and schema versions — all already carried by
   [`ReportMetadata`](../../creatoros/reporting/metadata.py)), is stored and never mutated.
2. **Be the durable source of findings.** Once stored, a snapshot can be re-read for
   presentation without recomputation — this is the store that `export --from-findings`
   ([ADR-007](../decisions/adr-007-report-export-command-surface.md)) reads from.
3. **Derive knowledge that only exists across time.** Change, trajectory, and persistence
   between snapshots: "cadence CV fell 0.55 → 0.31 over four months", "the top-outlier title
   pattern recurs in 3 of the last 4 snapshots". These are themselves descriptive,
   confidence-bounded observations — findings _about the history of findings_.
4. **Answer historical questions.** "What did we know about this channel six months ago?"
   "When did this pattern first appear?" The layer is the system's long-term memory for a
   channel, and — later — across channels.

## The rules every stored fact obeys

- **History is immutable and append-only.** A snapshot is written once and **never modified
  in place**, and never deleted. New analysis appends; it never overwrites. A correction is
  a **new revision** — a fresh entry that supersedes an earlier one by referencing it — never
  an edit to the original. The superseded entry stays readable exactly as first recorded, so
  what the system knew, and when, is always recoverable. History is added to, never rewritten.
- **Never recompute the past.** When metrics or intelligence code evolves, old snapshots
  stay exactly as they were written — computed under their own `metric_engine_version`. Re-
  deriving history with today's code would silently rewrite what the system "knew" and
  destroy the one thing this layer exists to protect. New code changes only new snapshots.
- **Consume findings, never reports.** Knowledge reads the `ChannelFindings` contract, the
  same immutable object Reporting reads. It never parses Markdown/HTML/JSON output — those
  are disposable presentations, and parsing them back would invert the whole architecture.
- **Descriptive, not predictive.** Storing history and describing change over time is
  description. Knowledge is the _substrate_ a future prediction layer would need, but it
  makes no forecast itself — the same discipline the rest of the system holds to.
- **Provenance travels with every fact.** A snapshot is meaningless without knowing what
  produced it; a full provenance header is stored with every entry (see the next section) so
  it can be read and trusted years later.

## Provenance — what every entry records

An archived snapshot is only trustworthy if you can tell exactly where it came from and
under what assumptions it was computed. Every Knowledge entry therefore stores, alongside
the findings themselves, an immutable provenance header written once with the entry and
never changed:

| Field | Meaning | Today |
|-------|---------|-------|
| CreatorOS version | the package version that produced the snapshot | `ReportMetadata.creatoros_version` |
| Metric engine version | the metrics code the findings were computed under | `ReportMetadata.metric_engine_version` |
| Findings schema version | the shape of the `ChannelFindings` contract itself, so an old entry stays readable after the contract changes | **new** — owned by the versioning work (#34); distinct from today's `report_format_version`, which versions a *report*, not the findings |
| Timestamp | when the snapshot was generated, UTC | `ReportMetadata.generated_at` |
| Source channel | the channel the findings describe | `ReportMetadata.channel_id` |
| Source findings identifier | a stable id for this exact snapshot, so a revision can name what it supersedes and a consumer can cite one specific entry | **new** — required for append-only revisions and traceability |

Four of the six fields already exist on [`ReportMetadata`](../../creatoros/reporting/metadata.py);
the two marked **new** — a findings _schema_ version and a stable snapshot identifier — are
the additions this layer needs, and they are the reason the versioning-strategy work is a
prerequisite. Together the six make every historical fact traceable to the code, the
contract, the moment, and the source that produced it — the guarantee the whole layer rests
on.

## Inputs

- **Canonical findings only.** A `ChannelFindings` plus its metadata, handed over
  immediately after the intelligence layer produces it. This is the sole input for anything
  Knowledge concludes — mirroring how intelligence consumes only derived metrics.
- **Not raw rows.** Knowledge never opens the ingestion database to read videos or
  transcripts. If a fact isn't in the findings, it isn't Knowledge's to know.
- **Not metrics.** It never calls `compute()` and never reads a derived value directly. It is
  two layers above the metrics engine and sees only what intelligence chose to surface.
- **Not reports.** Rendered output is never an input (see the rules above).

## Outputs

- **The findings archive:** a permanent, queryable series of snapshots per channel, each
  retrievable by time. This is the durable form of "findings are permanent."
- **Temporal knowledge:** deltas, trends, and persistence observations derived from the
  series — descriptive and confidence-bounded, never a prediction.
- **Consumers:** the reporting layer (a longitudinal report is just a renderer over temporal
  knowledge), the CLI (`export --from-findings`, historical queries), and — eventually — a
  separate prediction layer that this archive would feed. Knowledge outputs are, like
  findings, a stable contract others read; they are not rendered here.

## Permanence — where this layer sits in the store-vs-recompute hierarchy

CreatorOS has four kinds of data with four different permanence answers:

| Layer | Permanence | Why |
|-------|-----------|-----|
| **Raw** (SQLite) | Captured, authoritative once fetched | The source; re-fetching later yields *different* data, so what was captured is what happened. |
| **Metrics** (derived) | Recomputed, never stored (ADR-006) | Pure functions of raw rows; cheap at our scale; storing them adds a staleness problem. |
| **Findings** | **Persisted — permanent, immutable, append-only** | The one thing that **cannot be recomputed**: a snapshot describes data in a state that no longer exists. This is the Knowledge layer's charge. |
| **Reports** | Disposable, re-rendered on demand | Pure presentations of findings; deterministic renderers mean they are never worth storing. |

This is the concrete answer the persistence-strategy work (companion research) generalizes:
**recompute beats store, _unless_ the thing cannot be recomputed.** Findings-over-time is the
paradigm case where storage provides clear, irreplaceable long-term value — which is
precisely why the Knowledge layer, and not a cache, is where they live.

## Relationship with Findings

Findings are both the **input** and the **stored unit**. Knowledge is their custodian across
time: it accepts an immutable `ChannelFindings`, stamps it with provenance, and files it
into the channel's history, forever. It depends on two properties of the contract:

- **Immutability** — a stored finding must never change, so the contract's frozen dataclasses
  are load-bearing here, not just tidy.
- **Versioning** — a snapshot written under one schema must be readable years later, which is
  what a **finding schema version** (companion versioning note) must guarantee; Knowledge is
  its primary consumer.

Knowledge and Reporting are **siblings**, not a pipeline: both sit directly atop the findings
contract. The architecture's linear "→ Knowledge" reads as "findings flow into Knowledge for
permanence", parallel to "findings flow into Reporting for presentation" — Knowledge is never
downstream of a rendered report.

## Relationship with Metrics

None, directly — and that is the point. Metrics are recomputable and ephemeral; they live
inside the intelligence layer just long enough to produce a findings snapshot, and are gone.
Knowledge never sees them. The bridge between them is one-way and frozen at write time: a
snapshot records the `metric_engine_version` it was computed under, so history remains
interpretable even as the metric definitions evolve — but Knowledge never re-runs those
metrics against old data. Metrics can change freely tomorrow; the past stays as it was known.

## What the Knowledge layer must never do

- **Never mutate or delete a stored finding.** Append-only, always.
- **Never recompute historical findings with newer code.** History is not a cache to refresh.
- **Never parse a rendered report** to recover data — read the findings contract.
- **Never predict.** It is the substrate for prediction, not the predictor.
- **Never compute a metric or read a raw field.** It is two layers removed from both.
- **Never compile cross-channel personal data** beyond the descriptive, channel-level facts
  the findings already contain.

## Open questions (deferred, by design)

- **Storage mechanics.** Table(s) in the existing SQLite database vs a separate findings
  store vs JSON documents on disk — deferred to the persistence-strategy research. The
  contract here (append-only, immutable, provenance-stamped) constrains the choice without
  making it.
- **Snapshot identity and cadence.** What makes two snapshots "the same" analysis, how often
  a channel is re-analyzed, and how near-duplicate snapshots are handled. Ties to
  time-series snapshots ([#3](https://github.com/Deathroller789/CreatorOS/issues/3)).
- **Where temporal derivation lives.** Whether change-over-time observations are computed
  inside Knowledge or by a distinct "temporal intelligence" that consumes the archive the way
  today's intelligence consumes metrics. Leaning toward the latter as the series grows, but
  not decided here.
- **Schema evolution.** How a stored snapshot written under an old finding schema is read
  after the schema changes — owned by the versioning-strategy research.

## Non-goals

- No implementation, no storage schema, no code — this is the contract, not the build.
- No prediction, forecasting, or recommendation.
- No cross-channel intelligence yet; the single-channel history is the first job.

## Next actions

1. Companion research settles the mechanics this design depends on: versioning strategy
   (finding schema version ownership) and persistence strategy (what is stored vs recomputed).
2. Only then, a first implementation PR: persist each `ChannelFindings` snapshot append-only
   with its provenance, and let `export --from-findings` read it back — the smallest slice
   that makes "findings are permanent" real.
3. Temporal knowledge (deltas and trends across snapshots) follows once there is a history to
   derive it from.
