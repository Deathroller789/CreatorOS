# ADR-008: Versioning strategy — one software version, independent contract schemas

- **Status:** Accepted
- **Date:** 2026-07-13

## Context

CreatorOS already carries several version numbers, and the knowledge layer
([module 003](../modules/003-knowledge-layer.md)) is about to make one of them
load-bearing: a snapshot persisted today must stay readable years from now, against the
exact contract it was written under. That only works if we are clear about **what each
version means, who owns it, and when it changes** — before permanence sets the answer in
stone.

The versions in play today:

- **CreatorOS version** — `version` in `pyproject.toml` (`0.1.0`); the software release.
- **Report format version** — `REPORT_FORMAT_VERSION = 1` in
  [`metadata.py`](../../creatoros/reporting/metadata.py); the shape of a rendered report's
  provenance block.
- **Metric engine version** — stamped on every report, but currently **equal to the
  package version** (honest debt noted in `metadata.py`): the engine is not independently
  versioned yet.
- **Benchmark schema version** — `BENCHMARK_SCHEMA_VERSION = 1`
  ([`benchmark.py`](../../creatoros/benchmark.py)); the shape of a benchmark JSON record.
- **Findings schema version** — does **not exist yet**. Module 003's provenance header
  requires it, distinct from the report format version, and this ADR is its prerequisite.

The failure mode to avoid is the one already half-present: treating the package version as
a proxy for contract stability. If "the software released" and "the findings shape changed"
share a number, a stored snapshot can no longer tell whether its shape differs from today's
— which is exactly the question the knowledge layer must answer.

## Decision

**Separate the one human-facing software version from the machine-facing contract
schemas, and give every persisted contract its own version, owned where the contract lives
and changed only when that contract's *shape* changes.**

- **CreatorOS version — SemVer, owned by the release** (`pyproject.toml`). It answers "which
  build of the tool is this" for a human installing or reporting a bug. It is **not** a
  proxy for any contract's stability, and nothing downstream should infer schema
  compatibility from it.
- **Each schema version — a monotonic integer, owned by the module that defines the
  contract.** It answers the only question a stored document asks: "which shape am I, so a
  reader knows how to parse me." Specifically:
  - **Findings schema version** (new) lives with the findings contract
    ([`findings.py`](../../creatoros/intelligence/findings.py)) and bumps when a findings
    dataclass field is added, removed, renamed, or retyped.
  - **Metric engine version** lives with the metrics engine and bumps when a metric
    *definition* changes such that the same raw data yields different derived values.
    (Today it is pinned to the package version — debt; see Consequences.)
  - **Report format version** lives with the reporting metadata and bumps when a report's
    structure changes.
  - **Benchmark schema version** lives with the benchmark module and bumps on record-shape
    changes.

A version bumps on a change to **shape or definition**, never on a change to a **value**. A
new channel, a new view count, a different timing — none of these touch any version. This is
the line that keeps versions meaningful.

Stated plainly, as three rules:

- **Only CreatorOS uses Semantic Versioning.** It is the sole SemVer number in the system.
- **Every schema uses a simple, monotonically increasing integer** — `1`, `2`, `3`. No
  major/minor/patch, no dots, no gaps reused.
- **A schema version represents contract *shape* only, never values.** It changes when the
  structure changes and at no other time.

## When each changes

| Version | Scheme | Lives in | Bumps when | Does **not** bump when |
|---------|--------|----------|-----------|------------------------|
| CreatorOS | SemVer | `pyproject.toml` | any release (feature/fix) | a contract's shape changes with no release |
| Findings schema | integer | `intelligence/findings.py` | a findings field is added / removed / renamed / retyped | a value changes; analysis logic changes; a new release |
| Metric engine | integer* | `metrics/` | a metric definition/formula changes (same raw → different derived) | new data changes a value; a release with no metric change |
| Report format | integer | `reporting/metadata.py` | the report's structure / provenance block changes | a value changes; findings change; a restyle keeping the same fields |
| Benchmark schema | integer | `benchmark.py` | the record's shape changes | a timing value changes |

\* target scheme; today it equals the package version (debt).

Two axes people conflate, kept explicit here:

- **Findings schema vs metric engine** are orthogonal. One is the *shape* of the findings;
  the other is the *code that computed the values inside them*. A snapshot records both, and
  either can change without the other.
- **Report format vs findings schema** are independent. A report can be restructured without
  the findings changing, and findings can change without touching a report's layout.

## Compatibility

Not every contract carries the same compatibility promise, because not every contract is
persisted.

- **Findings schema — read-backward-compatible, as a standing goal.** Findings are stored
  permanently by the knowledge layer, so a newer CreatorOS release **should continue to read
  older findings schemas whenever reasonably possible**. A schema bump is expected to be
  *additive* by default — a new optional field, a new finding group — which older readers can
  ignore and newer readers can treat as absent on old entries. A genuinely breaking change
  (a field removed or retyped) is allowed but is the exceptional case, and it is what turns
  the optional "schema migration" work (below) from a nicety into a requirement. History is
  never rewritten to fit a new schema; the reader adapts to the old shape, not the reverse.
- **Report format — no backward-compatibility promise.** Reports are disposable and
  re-rendered from findings on demand, so there is nothing old to keep reading. The version
  exists only to label a report a human happened to save; CreatorOS is not obligated to parse
  an old one (and by "never parse rendered output", it will not).
- **Metric engine — not a compatibility concern, a provenance one.** Its version is never
  used to *read* anything; it records which code produced a stored snapshot so history stays
  interpretable. Old snapshots are never recomputed under a new engine version (module 003).
- **Benchmark schema — best-effort.** Records are local history; a reader of an old record
  should degrade gracefully, but no strong promise is made.

The load-bearing commitment is the first one: **future releases keep reading older findings
schemas whenever reasonably possible**, because that is what lets the knowledge layer promise
permanence without freezing the contract forever. When "reasonably possible" runs out, the
schema-migration research (optional future issue) is the escape hatch — designed only when a
real read-back across an incompatible bump first occurs, never speculatively.

## Alternatives

- **One unified version (everything tracks the package version).** The current, partial
  state. Rejected: it conflates software releases with contract stability, so a persisted
  snapshot cannot tell a shape change from a routine release — the knowledge layer's core
  question becomes unanswerable. It is the debt, not the target.
- **SemVer for the schemas too** (`findings 2.3.1`). Rejected: overkill for a stored
  document's shape. A reader of a snapshot asks one question — "which shape am I" — and a
  monotonic integer answers it. SemVer's major/minor/patch distinctions need a consumer who
  reasons about backward-compatible ranges; a stored snapshot does not. The package version
  *is* SemVer precisely because humans installing the tool are that consumer.
- **No schema versions; rely on the package version plus git.** Rejected: a stored snapshot
  has no access to git history or the build that wrote it. It must be self-describing, which
  means the version travels *in* the document.
- **Derive a version by hashing the dataclass structure.** Rejected: a structural hash is
  automatic but opaque and unorderable — you cannot tell which of two hashes is newer, and a
  reader cannot map it to a documented shape. An explicit integer bumped by a human when they
  change the contract matches the project's explicit-over-magic stance (ADR-006).

## Tradeoffs

- **Gain:** a persisted snapshot is self-describing and future-proof — the knowledge layer
  can store findings permanently and still read them after the contract evolves.
- **Gain:** each version means exactly one thing and changes for exactly one reason, so
  "did the shape change?" and "did the tool release?" are never confused.
- **Give up:** discipline is required — a contributor who changes a findings field must
  remember to bump the findings schema version. The golden files
  ([#29](https://github.com/Deathroller789/CreatorOS/issues/29)) are the backstop: a shape
  change that alters rendered output fails the regression until the golden files are
  deliberately regenerated, which is the natural
  moment to bump the version.
- **Give up:** several small integers instead of one number. Accepted — they are cheap, and
  each earns its keep by answering a distinct question.

## Consequences

- **Findings schema version is introduced** as a distinct integer on the findings contract,
  surfaced in provenance (module 003) alongside the existing fields. Its first value is `1`.
  This unblocks the knowledge layer's provenance header. Implementation lands with that work,
  not here.
- **The metric-engine-version debt is named with a target.** Today `metric_engine_version`
  equals the package version; the target is an independent integer bumped only on metric
  definition changes. The one-line change lives behind the existing comment in `metadata.py`;
  this ADR records *why* and *when* it should happen (roadmap
  [#19](https://github.com/Deathroller789/CreatorOS/issues/19) already tracks per-metric
  versioning, of which this is the engine-level rollup).
- **`report_format_version` stays as-is**, now explicitly scoped to reports, not findings —
  the two are no longer allowed to drift into meaning the same thing.
- **Revisit trigger:** the first time a stored snapshot must be *read back* under a newer
  schema (a real migration, not just a bump). That is when read-side handling of old schema
  versions gets designed — deferred until the knowledge layer actually persists something.

## Exit strategy

Trivial. These are integers and a SemVer string, no dependency. If the multi-version scheme
ever proves heavier than the permanence it buys, versions can be collapsed — but not before
anything is persisted, and the knowledge layer is the thing that makes them matter, so the
two decisions rise and fall together.
