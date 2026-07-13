# ADR-011: Non-scalar (corpus) evidence shape

- **Status:** Accepted
- **Date:** 2026-07-14

## Context

[RFC-002](../rfcs/rfc-002-what-is-evidence.md) defined evidence and its taxonomy, and named
its one architectural consequence: the Derived layer can express a **scalar per record**
(ADR-006), but *corpus* evidence — recurring phrases, keywords, opening/ending patterns
across a channel's videos — is a **table**, not a scalar. The Evidence Engine milestone
(issues [#45](https://github.com/Deathroller789/CreatorOS/issues/45),
[#46](https://github.com/Deathroller789/CreatorOS/issues/46),
[#47](https://github.com/Deathroller789/CreatorOS/issues/47)) needed this shape to use the
transcripts already being captured and to attribute what over/under-performers share.

The question RFC-002 left open: does the non-scalar shape live *inside* the metrics engine
(a metric that returns a structure), *beside* it (a new sibling "corpus producer" layer),
or is corpus aggregation *analysis* rather than a derived metric?

## Decision

Split the work along the RFC-002 evidence **levels**, with no new layer:

- **Per-video tokens are derived metrics.** A pure `*_tokens` metric (title, transcript,
  transcript opening/ending) returns that video's normalised token list — a Level-1 fact,
  reproducible from raw text, `None` when the text is absent. These are ordinary video-scope
  metrics carrying a `category` of `"corpus:<family>"`.
- **Recurrence across videos is analysis.** The intelligence layer aggregates those
  per-video token lists into recurring-phrase findings (document frequency, a support floor,
  the above/below split) — a Level-2/3 pattern *across* facts, which is what the analysis
  layer already does (it computes group means the same way).

The engine is unchanged: a metric value may be any type, and channel-scope aggregation of a
video-scope series already existed. Evidence is **discovered** by category
(`evidence_categories()`), so a new corpus family is one decorated function with no analysis
edit (ADR-006's promise, now realised for non-scalar evidence).

## Alternatives

- **A channel-scope metric returning the whole table.** Rejected: the above/below-baseline
  split (issue #47) joins corpus recurrence with *performance*, which a pure metric cannot
  see. Aggregation-with-context is analysis, not a derived fact.
- **A new "corpus producer" layer beside the engine.** Rejected as premature: it invents
  architecture for a shape the existing layers already express. Raw → Derived → Findings
  stays intact; nothing needed a fourth box.
- **LLM phrase/topic extraction.** Out of scope by RFC-002: gathering evidence is
  deterministic; an LLM may only *synthesise* over evidence later, and never produces it.

## Tradeoffs

- **Gain:** no engine change, no new layer, full ADR-006 preservation; corpus families are
  additive; the WHY split falls out naturally because analysis sees both corpus and
  performance; everything stays deterministic and inspectable.
- **Give up:** per-video token lists are stored as derived values (larger than scalars); the
  n-gram/support logic lives in `intelligence/corpus.py`, so the analysis layer now carries
  real text-processing (kept pure and dependency-free).

## Consequences

- Adding corpus evidence (comments, chapter titles, thumbnails-as-text) is a `corpus:*`
  token metric plus, if a bespoke shape is needed, a findings group — no engine work.
- **Narrative evidence** (RFC-002's far-term class) fits the same seam: opening/ending token
  metrics already exist; richer sequence signals extend the same pattern.
- **Revisit trigger:** if a future evidence class needs a *sequence*-shaped derived value
  that analysis cannot assemble from per-video metrics (e.g. cross-video alignment that must
  be reproducible and provenanced as a single fact), reopen this and consider a first-class
  non-scalar metric return or a dedicated producer.
