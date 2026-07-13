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

### Evidence exists to answer creator questions

This is the first and overriding principle; it gates every other.

> **Every piece of evidence must justify its existence by answering at least one creator
> question. If no creator question depends on it, it should not exist.**

CreatorOS is not an analytics product accumulating numbers because they can be measured. It is
an instrument for helping a creator discover truths about their own work that they could not
find by hand. A statistic that answers no question a creator would actually ask is not "extra
insight" — it is noise that dilutes the signal and spends trust.

The creator questions are the ones [Module 002](../modules/002-channel-intelligence.md) already
frames — *which videos over- or under-performed and what do they share; is my cadence helping or
hurting; what keeps a viewer watching* — plus the ones the roadmap will add. Each is a real
question a working creator asks. Evidence earns its place by tracing to one of them.

So the acceptance test has a **zeroth gate**, applied before the quality properties below:

- **Zeroth — necessity:** which creator question does this answer? If none, it does not ship.
- **Then — quality:** is it reproducible, provenanced, descriptive, confidence-bounded,
  inspectable?

An evidence class with no creator question behind it is a research curiosity, not a CreatorOS
feature.

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

### Levels of evidence

Evidence has **depth** as well as shape. Four levels — of which only the first three are
evidence. The fourth is what evidence is *for*.

- **Level 1 — Facts.** Individual reproducible observations about one video or channel: "this
  video runs 12 minutes, has a 47-character title, and earns 6,700 views/day." The atoms,
  computed directly from captured data.
- **Level 2 — Patterns.** Regularities *across* facts: "this channel uploads every 14 days";
  "40% of its titles pose a question"; "its videos fall into three topics." A pattern is many
  facts seen together.
- **Level 3 — Relationships.** Connections *between* facts and patterns: "above-baseline videos
  pose a question twice as often as below"; "outliers concentrate in one topic"; "cadence
  tightened as views grew." Descriptive association — never asserted as cause.
- **Level 4 — Explanations.** The causal "why": "this title worked *because* it opened a
  curiosity gap." **This is not evidence.** It is **synthesis** — an interpretation built on
  Levels 1–3, produced by reasoning over them, accountable to them, and forbidden to contradict
  them. It is the one place an LLM may eventually operate, and it must cite the evidence beneath
  it.

> **Levels 1–3 are evidence, gathered deterministically. Level 4 is synthesis — the only place
> interpretation lives.**

A system that blurs Level 3 into Level 4 — that lets a correlation be spoken as a cause — has
stopped being trustworthy. Keeping that line sharp is exactly what will let a creator trust the
"why" when it finally comes: it will be visibly built on facts they can inspect. The depth levels
and the shape classes below are two axes of the same thing — a Level-1 fact has a scalar shape, a
Level-2 pattern is corpus or temporal, a Level-3 relationship is comparative.

### The evidence taxonomy

Evidence also varies by **shape**, which fixes which layer produces it and whether it can be
deterministic. Six classes:

| Class | What it is | Shape | Layer | Deterministic? | Status today |
|-------|-----------|-------|-------|----------------|--------------|
| **Scalar** | One value per video or per channel: `views_per_day`, `performance_index`, `title_has_number`, cadence CV | one number per record | **Derived Metrics** | Yes | Exists (incl. title-structure evidence) |
| **Corpus** | An aggregate structure over the whole set: term/phrase frequency, recurring entities, lexical clusters | a table/set, not a scalar | **Derived** (new shape) | Yes (TF-IDF, RAKE, n-gram and entity rules are all deterministic) | Not built — the shape gap |
| **Comparative** | A relationship between observations: "above-baseline videos carry a number 2× as often"; "outliers concentrate in topic Y" | a contrast + effect size + n | **Findings** | Yes | Exists for scalars (Q2); extends to corpus evidence |
| **Temporal** | Change across snapshots: "cadence CV fell 0.55 → 0.31 over four months" | a delta over ≥2 snapshots | **Knowledge** | Yes (a diff) | Deferred — needs the findings archive |
| **Historical** | What was true at a past point: "in Q1 the top outlier was video X" | a retrieved past finding | **Knowledge** | Yes (retrieval) | Deferred — needs persistence |
| **Narrative** | Story structure *within* a video: hooks, curiosity gaps, conflict, escalation, callbacks, payoff, arc | a sequence/structure over one video's transcript | **Derived** (new shape) | Partly — the *signals* are; the *verdict* is synthesis | Future — the most valuable, most expensive class |

Three observations fall straight out of this table.

First, **evidence gathering is deterministic** — counting, comparing, diffing, and retrieving
need no LLM. The one class that reaches past what can be plainly counted is **Narrative**, and
the taxonomy handles it honestly: its *signals* are deterministic evidence (Levels 1–2), and its
*verdict* is Level-4 synthesis. Nothing an LLM produces is ever itself evidence.

Second, **the classes map onto the existing layers** — with the gaps being about *shape*, not
layer. Scalar → Derived, Comparative → Findings, Temporal/Historical → Knowledge are already how
the architecture is shaped. What the architecture cannot yet express is **non-scalar Derived
evidence**: the engine ([ADR-006](../decisions/adr-006-raw-derived-analysis.md)) returns a scalar
per record, but corpus evidence is a *table* and narrative evidence is a *sequence*. That
shape gap — not "how do we do topics" — is the real open question; RFC-001 is one instance of it,
and narrative is the harder one.

Third, **narrative evidence is likely the most valuable class CreatorOS will ever gather**, and
the most expensive. Story structure — the hook that stops the scroll, the curiosity gap that
holds attention, the escalation and payoff that earn a re-watch — is what creators most want to
understand and are least able to see across their own catalog. It also straddles the determinism
boundary, and the taxonomy keeps that honest: the *signals* are deterministically detectable — a
question posed in the first ten seconds (a curiosity gap opening), an entity from the intro
recurring at the end (a callback), rising pace or intensity (escalation), a resolved question (a
payoff) — and those are Level 1–2 evidence. The *judgment* that a hook is strong or suspense
well-built is Level-4 synthesis over those signals, cited back to them, never asserted as a bare
fact. CreatorOS gathers the narrative signals deterministically and leaves the narrative verdict
to synthesis.

### From evidence to knowledge

Evidence and knowledge are not the same thing, and evidence does not automatically become
knowledge. A single reproducible observation is evidence; it is not yet something the system — or
a creator — is entitled to *believe*. **Knowledge is evidence that has accumulated enough support
to justify belief.**

Support accumulates along four axes:

- **Repetition across many observations** — the same pattern seen in many videos of one channel.
- **Repetition across many channels** — the same pattern seen in many independent channels.
- **Consistency over time** — the pattern holding across snapshots, not just in one capture.
- **Agreement across independent evidence classes** — scalar, corpus, comparative, and temporal
  evidence pointing the same way, each derived by a different method.

So belief strengthens in stages:

> **A single observation is evidence. Repeated observations are stronger evidence. Independent
> evidence classes converging on the same conclusion begin to become knowledge.**

The last axis is the decisive one. Repetition and consistency strengthen evidence within its own
kind; *convergence* — different, independently derived evidence classes agreeing — is what turns
strong evidence into knowledge, because independent methods are unlikely to share the same error.
This is the arrow the architecture already names: Findings accumulate into **Knowledge**
([Module 003](../modules/003-knowledge-layer.md)), the layer where support is weighed across
observations, channels, and time.

Knowledge is not truth. **Truth exists independently of CreatorOS; knowledge is the strongest
explanation currently justified by the available evidence — our best justified understanding, not
a guarantee of truth.** Because knowledge is justified by evidence rather than identical to truth,
it always remains **revisable**: a stronger piece of evidence — a wider sample, a longer history, a
once-agreeing class that now disagrees — can revise or overturn it. The system holds knowledge the
way it holds findings: provisionally, provenanced, and open to being rewritten by better evidence.

> **CreatorOS does not search for certainty. It searches for convergence.**

Convergence between independent evidence streams is therefore not merely a quality signal — it is
the long-term direction of the product. What CreatorOS ultimately delivers is not any single
measurement but the moment several independent lines of evidence, gathered by different
deterministic methods, agree.

### When evidence disagrees

Convergence is earned, never assumed — and independent evidence classes will sometimes point in
different directions. When they do, **CreatorOS must preserve the disagreement rather than force a
conclusion.** If title-structure evidence suggests one account while transcript evidence suggests
another, the honest result is to report both and the tension between them — not to invent a single
answer the evidence does not support.

This follows directly from the definition of evidence: **disagreement is itself evidence.** A
contradiction between independently derived classes is a real, reproducible observation about the
channel, and suppressing it to manufacture a clean verdict would be exactly the laundering of
interpretation into fact that the levels forbid. Reported honestly, disagreement tells a creator
something true — that the picture is genuinely mixed.

> **Absence of convergence is not failure. It is an honest result.**

CreatorOS is therefore allowed to conclude **"we do not yet know."** That is a successful outcome,
not a product failure. The goal is not to maximise the number of conclusions the system reaches,
but to maximise the number of *truthful* ones. A system that always produces an answer has stopped
being accountable to its evidence; one that says "not yet" when the evidence has not converged is
behaving exactly as this framework requires.

### Evidence grows more expensive, and more valuable

A guiding principle — and the shape of the long-term roadmap:

> **Evidence should become increasingly expensive to compute, and increasingly valuable to
> creators — and its destination is not any single expensive class, but multiple independent
> evidence classes converging on the same conclusion.**

The cheap evidence comes first because it is the foundation — but it is also the least
differentiated: a creator can eyeball their own title lengths. The expensive evidence comes later
because it is hard — but it is where CreatorOS earns its reason to exist, because a creator
*cannot* eyeball the narrative structure of fifty videos or the topic-conditioned performance of
a whole catalog. Cost and value rise together, and that ordering *is* the roadmap:

| Stage | Evidence | Cost | Why a creator can't do it by hand |
|-------|----------|------|-----------------------------------|
| 1 | Scalar facts (title/format structure, cadence) | trivial | mostly confirms what they already suspect |
| 2 | Corpus patterns (topics, recurring phrases/entities) | moderate | reveals what a channel is *actually* about, at scale |
| 3 | Relationships (what hits share; topic-conditioned performance) | moderate–high | isolates packaging from topic — genuinely hard by hand |
| 4 | Temporal / historical (trajectory across snapshots) | high | shows change no single snapshot can |
| 5 | Narrative evidence (hooks, curiosity gaps, escalation, payoff) | highest | the truths creators most want and least can see |

Synthesis (Level-4 explanations) sits above all of it, consuming whatever evidence exists. The
discipline the principle enforces cuts both ways: **do not chase expensive evidence before the
cheap foundation it rests on exists**, and **do not stop at the cheap evidence, because the
expensive evidence is the point.** Every stage is justified only by the creator questions it
answers (the zeroth gate), and each becomes tractable only once the stage beneath it exists.

But the gradient is not just a ladder of rising cost; the stages are the independent evidence
streams whose *convergence* is the real goal. The destination of CreatorOS is not the most
expensive class in isolation — narrative evidence for its own sake — but **multiple independent
evidence classes converging on the same conclusion** (see
[From evidence to knowledge](#from-evidence-to-knowledge)): scalar, corpus, comparative, temporal,
and narrative evidence, each gathered by a different deterministic method, agreeing on the same
account of why a video performed. That convergence — not any single measurement — is the real
destination this gradient climbs toward, and it is what a creator can finally trust.

### The determinism boundary

The line between evidence and explanation is the Level-3 / Level-4 line, restated operationally
as deterministic gathering versus interpretive synthesis.

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

1. **The Derived layer must gain a way to represent non-scalar evidence** without breaking the
   scalar engine — a deterministic producer (a channel-scope component that returns a structure)
   feeding Findings, alongside the scalar metric engine. Corpus evidence needs a *table*;
   narrative evidence needs a *sequence*. Whether this lives *inside* the engine (a metric
   returning a structure) or beside it (a sibling derived component) is the ADR-006 "shape"
   question, now generalised beyond topics. Corpus is the near-term instance; narrative is the
   far-term one and will also need its determinism boundary drawn per signal.
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

- **It is product-first, not statistic-first.** The necessity gate ("which creator question does
  this answer?") stops CreatorOS from accumulating measurable-but-useless numbers — the failure
  mode of every analytics tool it refuses to become.
- **The levels keep two dangerous lines sharp** — correlation vs cause (Level 3 vs 4) and
  evidence vs synthesis — so the LLM can never launder an interpretation into a fact, and a
  future "why" is visibly built on inspectable facts.
- **One definition instead of many ad-hoc ones.** Every future evidence question (phrases,
  entities, thumbnails, comments, narrative) is answered by placing it in the taxonomy and the
  levels, not by relitigating shape and layer each time.
- **The cost/value gradient is a ready-made roadmap** that also enforces discipline: build the
  cheap foundation first, but don't stop there, because the expensive evidence (narrative) is the
  point.
- **It is fully consistent with every accepted ADR** — it names and organises principles already
  present in ADR-006/009/010 and Module 002/003, rather than introducing new ones.

## Cons

- **It is a framework, not a shipped feature** — its value is realised only when the enacting
  work (the non-scalar shape decision) is done. A principles document that never gets enacted is
  overhead.
- **The necessity gate needs a maintained question set.** "Answers a creator question" is only
  enforceable if the catalogue of creator questions is kept current (it starts from Module 002's
  Q1–Q6); an out-of-date list would gate wrongly.
- **Narrative evidence's determinism boundary is genuinely hard.** Which narrative signals are
  reproducibly countable (curiosity-gap opener, callback, escalation, payoff) and which collapse
  into Level-4 judgement must be drawn per signal — the RFC sets the rule but not every ruling.
- **The taxonomy could still be incomplete.** Cross-channel/relational evidence may need yet
  another class; the framework must grow a class rather than force a bad fit.

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

Adopt this definition of evidence, its levels, and its taxonomy as the frame for all Evidence
Engine work. Concretely:

1. **Accept the necessity gate** — evidence exists only to answer a creator question — as the
   zeroth test, ahead of the five quality properties (reproducible, provenanced, descriptive,
   confidence-bounded, inspectable; immutable once recorded).
2. **Accept the four levels** (Facts, Patterns, Relationships = evidence; Explanations =
   synthesis) and the six shape classes (scalar, corpus, comparative, temporal, historical,
   narrative), with the determinism boundary: LLM = synthesis only, never a producer of evidence.
3. **Accept the cost/value gradient as the roadmap** — cheap facts first, narrative evidence
   last, each stage justified by a creator question and enabled by the stage beneath it.
4. **Treat the non-scalar evidence shape as the next architectural decision** — a single ADR for
   how the Derived layer represents a *table* (corpus) and, later, a *sequence* (narrative),
   generalising the shape question RFC-001 raised for topics. Corpus is the near-term instance it
   unblocks.
5. **Keep temporal/historical evidence, narrative evidence, and all synthesis out of scope** until
   their prerequisites (findings archive; sequence shape; a citation-bound synthesis layer) exist.

Confidence: **High** on the framework — it restates and organises principles the repo already
commits to, and the product-first gate makes it more, not less, grounded. **Medium** on the
taxonomy's completeness: cross-channel/relational evidence may still require a further class, and
narrative's determinism boundary will need per-signal rulings. The framework should grow a class
rather than distort to fit.

## Open questions

- **Non-scalar evidence shape** — channel-scope producer returning a structure (table, then
  sequence) vs a separate derived component. The concrete decision consequence 1 defers to an
  enacting ADR.
- **The creator-question catalogue** — where the authoritative list of creator questions lives
  and how it is kept current, since the necessity gate depends on it (starts from Module 002's
  Q1–Q6).
- **Narrative signal boundaries** — exactly which narrative signals are reproducibly countable
  (Level 1–2 evidence) versus interpretive (Level-4 synthesis). Drawn per signal against the five
  properties.
- **The grey-zone methods** — entities and sentiment: admitted as deterministic evidence only
  where a reproducible rule-based method exists, else pushed to synthesis.
- **A possible further class** — relational/cross-channel evidence (`compare-channels`) may not
  fit the six classes. Left open; add a class if and when it is real.

## Next actions

- Circulate for the decision on the definition and taxonomy (this RFC).
- On acceptance, open the **corpus-evidence shape ADR** (consequence 1) — the one architectural
  decision that unblocks the corpus classes; RFC-001's method spike feeds it.
- Only then build corpus evidence as additive Derived producers + Findings groups, method chosen
  by RFC-001's spike.
- Hold temporal/historical evidence for the Knowledge layer, and synthesis for last.
