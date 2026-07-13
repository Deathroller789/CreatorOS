# ADR-010: Persistence philosophy — what deserves to become history

- **Status:** Proposed
- **Date:** 2026-07-13

## Context

Every layer of CreatorOS produces data — raw rows, derived metrics, findings, rendered
reports, and the temporal knowledge built from findings over time.
The lazy instinct is to store all of it "to be safe."
For a system meant to be trusted a year from now, that instinct is backwards: a stored copy
of something that could have been recomputed will drift from its source the moment the source
or the code changes, and a stale copy that still looks authoritative is worse than no copy —
it lies with confidence.

The real question is therefore not "what should we store?" but **"what deserves to become
history?"** — what must be preserved because it can never be reconstructed.
[ADR-006](adr-006-raw-derived-analysis.md) already answered this for metrics (recompute,
never store), and [Module 003](../modules/003-knowledge-layer.md) sketched a four-kind
hierarchy while deferring the storage mechanics.
This ADR generalizes both into the definitive persistence philosophy for CreatorOS and
resolves the mechanics Module 003 left open.

## Decision

The principle, stated two ways:

> **Recompute > Store** — a thing is persisted only when historical value justifies it.
> A thing *deserves to become history* only if losing it would lose truth that cannot be
> regenerated.

Three tests decide every layer:

- **Historical value** — does a past instance carry irreplaceable meaning, or only
  present-moment convenience?
- **Recompute cost** — how hard is it to regenerate from what we already keep?
- **Cost of wrongness if lost** — if it vanishes, do we lose *truth* (unrecoverable) or merely
  *time* (recoverable by recomputing)?

A layer earns persistence only when historical value is real **and** recompute is *impossible*
— not merely expensive. Expense alone is a **caching** question, never a persistence one (see
Alternatives).

### Every layer, evaluated

| Layer | Historical value | Recompute cost | Cost of wrongness if lost | Decision |
|-------|------------------|----------------|---------------------------|----------|
| **Raw** | High — a later re-fetch yields *different* data; the capture *is* the historical fact | Impossible (re-fetching is not recomputing — the past state is gone) | **Truth lost** — irreplaceable | **Persist** — captured, authoritative, immutable once fetched |
| **Metrics** | None — a pure function of raw; a past metric is just old arithmetic | Microseconds | Time only — recompute from raw | **Recompute, never store** (ADR-006) |
| **Findings** | Highest — a snapshot describes data in a state that no longer exists | Impossible — the raw it described has since moved on | **Truth lost** — the one thing no re-run recovers | **Persist** — permanent, immutable, append-only |
| **Reports** | None — a deterministic serialization of findings | Milliseconds (re-render) | Time only — re-render from findings | **Disposable** — re-rendered on demand |
| **Knowledge** (temporal) | Derived — deltas/trends *across* snapshots | Cheap, given the findings archive | Time only — recompute from the archive | **Recompute** from the persisted findings archive; not stored separately |

### The rule underneath the table

Exactly two layers earn persistence — **Raw** and **Findings** — and both for the *same*
reason: each is a **capture of a moment that re-acquisition would change**.
A raw fetch captures a channel as it was that day; a findings snapshot captures what was true
about it then.
Everything else is a **derivation** — a deterministic function of a capture — and derivations
are always recomputed:

- Metrics derive from Raw (ADR-006).
- Reports derive from Findings (deterministic renderers, ADR-007).
- Temporal knowledge derives from the *archive* of Findings — the same relationship metrics
  have to raw, one level up.

So the four-kind hierarchy collapses to one line:

> **Persist captures. Recompute derivations.**

The persisted set is precisely the set of irreproducible captures, and nothing more.
A capture cannot drift, because it can never be regenerated to disagree with itself; a
derivation is never stored, so it can never go stale.

### Storage mechanics (resolving Module 003's deferred question)

The findings archive is an **append-only table in the existing SQLite database** — not a
separate store, not JSON files on disk.
Each row carries the six provenance fields from Module 003 promoted to real columns
(snapshot id, channel id, timestamp, CreatorOS version, metric-engine version, findings-schema
version) plus the **canonical findings serialized as a JSON blob**, stamped with its
findings-schema version ([ADR-008](adr-008-versioning-strategy.md)).

- **Same store as Raw** → one portable file, one backup, one exit path — consistent with
  [ADR-003](adr-003-why-stdlib-sqlite3-no-orm.md) and the reuse audit's "our data outlives our
  tools."
- **Append-only + immutable by construction** → the write path only ever `INSERT`s; there is
  no `UPDATE`/`DELETE` on the archive. A correction is a **new row** that references the id it
  supersedes, never an edit (Module 003's revision rule).
- **Provenance as columns, findings as an opaque blob** → provenance is what we *query* (list a
  channel's snapshots by time), so it is promoted to columns; the findings body is read *whole*
  by its consumers and never queried into, so it stays a versioned JSON blob. This keeps a
  stored snapshot readable under its own schema version forever, and avoids a schema migration
  every time the findings contract evolves.

## Alternatives

- **Store everything "to be safe" (materialize every layer).** Rejected: storing a derivation
  does not make the system safer, it makes it *less* trustworthy — a materialized metric or
  report drifts from its source the instant the source or the code changes, and a confident
  stale value is worse than none. Directly contradicts ADR-006.
- **Store nothing; recompute all.** Rejected: impossible for Raw and Findings, which are
  captures, not derivations. "Recomputing" a past finding is not recomputation — it is
  fabrication, because the data it described no longer exists to recompute from.
- **A separate findings store** (its own database or service). Rejected: it splits the
  single-file portability that makes the exit strategy trivial — two backups, two truths, and
  no transactional consistency with the raw capture.
- **JSON documents on disk, one file per snapshot.** Tempting for git-friendliness, rejected:
  the archive is *data*, not source. On-disk files lose transactional integrity with the raw
  capture and turn "list this channel's snapshots over time" into a directory walk instead of a
  query.
- **Normalized findings columns** instead of a JSON blob. Rejected: it forces a schema
  migration on every change to the findings contract and re-introduces the very
  immutability/versioning problem the versioned blob sidesteps.
- **Caching expensive derivations.** *Not an alternative — a different question, explicitly out
  of scope.* A cache is a performance optimization keyed on inputs and invalidated when they
  change; it is never a historical record. If a metric becomes too slow (ADR-006's revisit
  trigger), materialize it as a **cache**, not as history. The line is firm: **persistence
  answers "what is true and what was true"; caching answers "what is slow."** Never conflate
  them.

## Tradeoffs

- **Gain:** nothing stored can silently go stale, because the only stored things cannot be
  regenerated at all. Every derived view is always consistent with its source by construction.
- **Gain:** the persisted set is minimal — two captures (Raw, Findings) in one SQLite file — so
  backup, portability, and the exit strategy stay trivial.
- **Give up:** recompute cost paid on every read of a derivation. Accepted at our scale
  (ADR-006); if a derivation ever becomes expensive, that is revisited as a *caching* decision,
  not a persistence one.
- **Give up:** the findings body is opaque JSON, not queryable in SQL. Accepted — findings are
  read whole by their consumers, and the provenance columns carry everything we actually query
  on.

## Consequences

- Module 003's four-kind hierarchy is now the definitive philosophy, generalized to one rule:
  **persist captures, recompute derivations.** Future layers are classified by that test, not
  by convenience.
- **Storage mechanics are resolved:** an append-only findings table in the existing SQLite
  database, provenance promoted to columns, the findings body a versioned JSON blob. This
  unblocks Module 003's first implementation PR — persist each `ChannelFindings` snapshot with
  its provenance, and let `export --from-findings` (ADR-007) read it back — to be built **after**
  the real-channel usage phase, not now.
- **Temporal knowledge is a derivation of the findings archive** and is recomputed, never
  stored separately. Should it ever become too slow to recompute across a long history, that is
  a *caching* decision (a temporal cache), never a new historical record.
- **Findings-schema versioning (ADR-008) is load-bearing here:** every stored row is stamped
  with its schema version so a snapshot stays readable under its own contract years later.
- **Revisit trigger:** the first derivation too slow to recompute at read time (→ cache it, do
  not historicize it), or the first genuinely new *capture* beyond Raw and Findings — a new
  point-in-time acquisition that re-acquisition would change.

## Exit strategy

Trivial, and unchanged from ADR-003 and the reuse audit: everything persisted lives in one
portable SQLite file, with the findings body stored as plain JSON readable by any language or
tool. No new dependency and no new store is introduced. If this philosophy is ever proved
wrong, it is reworded in one document; the data is already in the most portable form there is,
so no migration of *data* is implied by a change of *policy*.
