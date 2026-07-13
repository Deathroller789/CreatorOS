# RFC-002: What is evidence in CreatorOS?

- **Status:** Proposed
- **Date:** 2026-07-13

## Context

CreatorOS is entering the Evidence Engine phase: gathering deterministic observations that a
later layer can turn into reliable explanations of *why* content performs.
Before deciding how any single kind of evidence (transcript phrases, topics, entities) is
represented, one question must be answered from first principles, because every later choice
depends on it: **what does CreatorOS consider evidence at all?**

[RFC-001](rfc-001-topic-representation.md) asked a narrower question — how to represent topics
— and correctly deferred the method choice.
But "topics" is not a primitive; it is one instance of a larger category the system has never
defined.
Answering the general question first makes the specific ones (RFC-001 included) fall out as
regions of a single framework, instead of a series of unrelated shape decisions.

This RFC therefore defines evidence: what counts, what does not, the properties evidence must
have, and where each class of evidence lives in the existing architecture
(Raw → Derived → Findings → Knowledge).
It deliberately reaches implementation **last** — the representation choices should be
consequences of the principles, not their starting point.
It changes no architecture and enacts nothing; an accepted RFC is followed by additive work
under the existing ADRs.

## First principles

### What evidence is

> **Evidence is a reproducible, provenanced, descriptive observation about a channel, derived
> from captured data, that a later explanation can be held accountable to.**

Evidence is not the explanation.
It is the factual substrate an explanation must cite and cannot contradict.
CreatorOS gathers evidence deterministically; interpreting it into a "why" is a separate,
downstream act (see [Synthesis](#the-determinism-boundary)).
This mirrors the charter the system already holds to — descriptive, not predictive
([Module 002](../modules/002-channel-intelligence.md)); never invent a fact
([ADR-006](../decisions/adr-006-raw-derived-analysis.md)); preserve uncertainty
([ADR-009](../decisions/adr-009-error-philosophy.md)).

### The five properties every piece of evidence must have

A thing is evidence in CreatorOS only if it is all five. These are the acceptance test.

| Property | Meaning | Grounded in |
|----------|---------|-------------|
| **Reproducible** | Same captured inputs produce the same observation, every time. Gathering evidence is deterministic. | ADR-006 (derived layer never invents facts) |
| **Provenanced** | Traceable to the exact data it came from and the code/version that produced it. | ADR-009, ADR-010 |
| **Descriptive** | A statement about what is or was — never a prediction, never a prescription. | Module 002 |
| **Confidence-bounded** | Travels with its sample size and honest uncertainty; never a bare assertion. | Module 002 |
| **Inspectable** | A human can verify it from the stored data by the same deterministic path. | ADR-010 (every intermediate representation inspectable) |

A sixth property applies once evidence is *recorded* rather than recomputed: **immutable**.
A finding, once written, is frozen and never rewritten (ADR-010, Canonical Findings).

### What is not evidence

Naming the boundary is as important as naming the thing.

- **An explanation or interpretation** ("this title worked because it created curiosity") — a
  claim *about* evidence, produced by reasoning over it. It is synthesis, and it lives
  downstream. It may cite evidence; it is not evidence.
- **A prediction** ("this will get 100k views") — outside the charter entirely.
- **A recommendation** ("use shorter titles") — prescriptive; forbidden (Module 002).
- **A non-reproducible output** — anything an LLM free-generates. It cannot be the factual
  basis for anything, because re-running it may differ. An LLM can *synthesise* evidence; its
  prose is never itself evidence.
- **A number without provenance or sample size** — fails the properties above; a bare
  assertion, not evidence.
- **Raw data on its own** — captured rows are the *source* of evidence, not evidence. A view
  count becomes evidence only once observed in a way that bears on a question (age-normalised,
  compared to a baseline, counted across a corpus). Raw is the substrate; evidence is the
  observation over it.

### The evidence taxonomy

Evidence varies along one axis that decides almost everything: its **shape**, which in turn
fixes which layer produces it and whether it can be deterministic. Five classes:

| Class | What it is | Shape | Layer | Deterministic? | Status today |
|-------|-----------|-------|-------|----------------|--------------|
| **Scalar** | One value per video or per channel: `views_per_day`, `performance_index`, `title_has_number`, cadence CV | one number per record | **Derived Metrics** | Yes | Exists (incl. title-structure evidence) |
| **Corpus** | An aggregate structure over the whole set: term/phrase frequency, recurring entities, lexical clusters | a table/set, not a scalar | **Derived** (new shape) | Yes (TF-IDF, RAKE, n-gram and entity rules are all deterministic) | Not built — the shape gap |
| **Comparative** | A relationship between observations: "above-baseline videos carry a number 2× as often"; "outliers concentrate in topic Y" | a contrast + effect size + n | **Findings** | Yes | Exists for scalars (Q2); extends to corpus evidence |
| **Temporal** | Change across snapshots: "cadence CV fell 0.55 → 0.31 over four months" | a delta over ≥2 snapshots | **Knowledge** | Yes (a diff) | Deferred — needs the findings archive |
| **Historical** | What was true at a past point: "in Q1 the top outlier was video X" | a retrieved past finding | **Knowledge** | Yes (retrieval) | Deferred — needs persistence |

Two observations fall straight out of this table.

First, **evidence gathering is deterministic in every class.** Not one class requires an LLM to
*produce* the evidence — counting, comparing, diffing, and retrieving are all deterministic.
This is not a constraint imposed on the taxonomy; it is a property the taxonomy reveals.

Second, **the classes map cleanly onto the existing layers** — with exactly one gap.
Scalar → Derived, Comparative → Findings, Temporal/Historical → Knowledge are already how the
architecture is shaped. The single thing the architecture cannot yet express is **corpus
evidence**: the Derived engine ([ADR-006](../decisions/adr-006-raw-derived-analysis.md))
returns a scalar per record, and a term-frequency table is neither. That gap — not "how do we
do topics" — is the real open question, and RFC-001 is one instance of it.

### The determinism boundary

The line between evidence and explanation is the line between deterministic gathering and
interpretive synthesis.

- **Everything that can be counted, compared, diffed, or retrieved is deterministic evidence**,
  and is produced by Python/SQLite in the Derived, Findings, or Knowledge layers. No LLM.
- **Synthesis** — turning a body of evidence into a human "why" — is the *only* place an LLM
  belongs, and it is a **separate future layer over Findings/Knowledge, never a producer of
  evidence.** It reasons; it does not measure. It must cite the deterministic evidence it rests
  on, and it can never contradict it.

Restated as the rule the system already half-holds (ENGINEERING.md principle 3, the user's LLM
rule):

> **If it can be counted, it is deterministic evidence. If it must be interpreted, it is
> synthesis over evidence — and synthesis is never evidence itself.**

An LLM topic *label* is interpretation (synthesis); a deterministic term-frequency table is
evidence. The label may later be produced by synthesis over the table — but the table comes
first, and the system's trust rests on the table, not the label.

## What follows for implementation (consequence, not premise)

These are not decisions this RFC makes; they are what the principles force, listed so the
enacting work is obvious once the frame is accepted.

1. **The Derived layer must gain a way to represent corpus evidence** without breaking the
   scalar engine — a deterministic corpus-evidence producer (a channel-scope component that
   returns a structure) feeding Findings, alongside the scalar metric engine. Whether it lives
   *inside* the engine (a channel metric returning a table) or beside it (a sibling derived
   component) is the ADR-006 "shape" question, now generalised beyond topics.
2. **The Findings contract grows additively** to carry corpus and comparative evidence (e.g.
   topic/entity/phrase finding groups), schema-versioned per
   [ADR-008](../decisions/adr-008-versioning-strategy.md). No rewrite; new frozen groups.
3. **Temporal and historical evidence wait on the findings archive** (persistence, ADR-010 /
   [Module 003](../modules/003-knowledge-layer.md)); they are Knowledge-layer work, recomputed
   from stored findings, and out of scope until the archive exists.
4. **Synthesis (LLM) is last and separate.** It is not built until deterministic evidence across
   the near-term classes exists, and even then it is a distinct layer that cites evidence — its
   output re-enters nothing as a fact (ADR-010: reports/interpretations never become inputs).
5. **RFC-001 is reframed, not replaced.** Topics are *corpus lexical evidence* — one region of
   this taxonomy. Its method comparison (TF-IDF vs RAKE vs …) and its spike still stand; they
   now answer "how do we produce this one class of corpus evidence," under the shape decision
   from consequence 1.

## Pros

- **One definition instead of many ad-hoc ones.** Every future evidence question (phrases,
  entities, thumbnails, comments) is answered by placing it in the taxonomy, not by relitigating
  shape and layer each time.
- **The determinism boundary becomes a bright line**, which protects the system's core promise:
  trust rests on reproducible facts, and the LLM can never launder an interpretation into a
  fact.
- **It surfaces the real gap** (corpus-evidence shape) that "how do we do topics" obscured, and
  shows it is a single decision serving many features, not a topics-only detail.
- **It is fully consistent with every accepted ADR** — it names and organises principles already
  present in ADR-006/009/010 and Module 002/003, rather than introducing new ones.

## Cons

- **It is a framework, not a shipped feature** — its value is realised only when the enacting
  work (corpus-evidence shape) is done. A principles document that never gets enacted is
  overhead.
- **The taxonomy could ossify.** A future evidence kind might not fit the five classes cleanly
  (e.g. graph/relational evidence across channels); the framework must be allowed to gain a
  class rather than forcing a bad fit.
- **The determinism line has grey zones.** Named-entity recognition and sentiment sit between
  "counted" and "interpreted"; the RFC holds them to the deterministic side only when a
  rule-based, reproducible method exists, and pushes them to synthesis otherwise — a judgement
  that will need to be made per method.

## Benchmarks / evidence

None to run — this is a principles RFC, not a method comparison.
Its evidence is internal consistency with the accepted architecture: the taxonomy is derived
from [ADR-006](../decisions/adr-006-raw-derived-analysis.md) (deterministic derived facts),
[ADR-010](../decisions/adr-010-persistence-strategy.md) (persist captures, recompute
derivations; inspectable intermediates), [ADR-009](../decisions/adr-009-error-philosophy.md)
(provenance, preserve uncertainty), and [Module 002](../modules/002-channel-intelligence.md) /
[Module 003](../modules/003-knowledge-layer.md) (descriptive, confidence-bounded, append-only
history). The one empirical question it exposes — which corpus-evidence method separates real
topics — is RFC-001's spike, unchanged.

## Prior art / community feedback

- **Internal, load-bearing:** ADR-006 (Raw → Derived → Analysis), ADR-009 (provenance /
  unavailable-vs-missing), ADR-010 (persist captures, recompute derivations), Module 002
  (evidence + confidence + sample size, never invent a fact), Module 003 (append-only findings
  history), and [RFC-001](rfc-001-topic-representation.md) (topic method comparison, now a
  region here).
- **External framing:** the evidence/interpretation split is the standard separation between
  *measurement* and *inference*; CreatorOS's stance is that measurement is deterministic and
  reproducible, and inference (synthesis) is explicitly downstream and citational.

## Recommendation

Adopt this definition of evidence and its taxonomy as the frame for all Evidence Engine work.
Concretely:

1. **Accept the five properties** (reproducible, provenanced, descriptive, confidence-bounded,
   inspectable; immutable once recorded) as the acceptance test for anything the system calls
   evidence.
2. **Accept the five classes** (scalar, corpus, comparative, temporal, historical) and their
   layer mapping, and accept the determinism boundary (LLM = synthesis only, never a producer of
   evidence).
3. **Treat "corpus-evidence shape" as the next architectural decision** — a single ADR that
   decides how the Derived layer represents non-scalar deterministic evidence, generalising the
   shape question RFC-001 raised for topics. That ADR, once made, unblocks corpus evidence
   (phrases, entities, topics) as additive Findings.
4. **Keep temporal/historical evidence and all synthesis out of scope** until their
   prerequisites (findings archive; then a citation-bound synthesis layer) exist.

Confidence: **High** on the framework (it is a restatement and organisation of principles the
repo already commits to). **Medium** on the taxonomy's completeness — cross-channel/relational
evidence may later require a sixth class; the framework should grow a class rather than distort
to fit.

## Open questions

- **Corpus-evidence shape** — channel-scope metric returning a structure vs a separate derived
  component. The concrete decision consequence 1 defers to an enacting ADR.
- **The grey-zone methods** — entities and sentiment: admitted as deterministic evidence only
  where a reproducible rule-based method exists, else pushed to synthesis. Decided per method,
  against the five properties.
- **A possible sixth class** — relational/cross-channel evidence (`compare-channels`) may not be
  scalar, corpus, temporal, or historical. Left open; add a class if and when it is real.

## Next actions

- Circulate for the decision on the definition and taxonomy (this RFC).
- On acceptance, open the **corpus-evidence shape ADR** (consequence 1) — the one architectural
  decision that unblocks the corpus classes; RFC-001's method spike feeds it.
- Only then build corpus evidence as additive Derived producers + Findings groups, method chosen
  by RFC-001's spike.
- Hold temporal/historical evidence for the Knowledge layer, and synthesis for last.
