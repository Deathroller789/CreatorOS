# RFC-001: How should CreatorOS represent topics?

- **Status:** Proposed
- **Date:** 2026-07-11

## Context

Channel Intelligence needs topics for three questions — Q4 (dominant topics), Q5 (content
clusters), and Q6 (topic-conditioned underperformers) — all deferred behind this RFC
([#21](https://github.com/Deathroller789/CreatorOS/issues/21)) in the module design
([002-channel-intelligence.md](../modules/002-channel-intelligence.md)). No topic code ships
until this decision is made.

The decision has **two coupled parts**:

1. **Method** — how topics are extracted from a channel's titles and transcripts.
2. **Shape** — how the result sits in Raw → Derived → Analysis
   ([ADR-006](../decisions/adr-006-raw-derived-analysis.md)). The engine returns a *scalar*
   per video or per channel; a term-frequency **table** is neither. So a method implies a
   shape: a channel-scope metric that returns a structure, a separate derived component, or
   something that lives in the Analysis layer entirely.

Binding constraints from [ENGINEERING.md](../ENGINEERING.md): stdlib first; no dependency
without an evaluation and an ADR; LLMs only for reasoning, not for what Python can do
deterministically; embeddings / vector search (Chroma) already
[deferred](../../research/technology/chroma.md); the Derived layer is **deterministic and
never invents facts**; intelligence is **descriptive, not predictive**.

**This RFC compares six approaches and deliberately does not pick one.** A decision now would
be premature: the right method depends on scope choices (is Q5 clustering near-term? is
cross-channel comparison?) that are not yet made. The job here is to lay out the tradeoffs
and the criteria that will settle it.

## Proposal

Evaluate topic representation on the axes that matter for *this* system, not on popularity:

- **Determinism** — same input, same output? This is the decisive axis: it decides whether
  topics can be a **Derived** metric (deterministic) or must live in **Analysis**
  (interpretive). A metric that "never invents a fact" cannot be non-deterministic.
- **Dependency weight** — stdlib, a new library (evaluation + ADR required), or a model/API.
- **Corpus need** — works per-document, or needs a background corpus.
- **Output type** — ranked terms, keyphrases, dense vectors, or fixed categories.
- **Semantic vs lexical** — does it model meaning, or match surface words?
- **Cross-channel comparability** — reusable for Sprint 4+ (`compare-channels`)?
- **Exit difficulty** — if the tool dies, how hard to replace? (Charter: reject anything
  worse than Low without a wrapper.)

## Comparison

| Approach | Output | Determinism | Dependency | Corpus | Semantic | Cross-channel | Exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **TF-IDF** | weighted terms / n-grams | Full | **stdlib**-viable (or `scikit-learn`) | needs a corpus for IDF | No (lexical) | Medium (needs shared IDF) | None |
| **RAKE** | keyphrases | Full | **stdlib**-viable (pure impls exist) | per-document | No (co-occurrence) | Low | None |
| **YAKE** | scored keyphrases | Full | **new dep** (`pke`→NLTK+spaCy, or `yake`) | per-document | No (statistical) | Low | Low |
| **Embeddings** (KeyBERT / sentence-transformers) | dense vectors + nearest terms | Per fixed model (version-fragile) | **heavy** (PyTorch; lighter via Model2Vec) | model *is* the prior | Yes | High | Medium–High (+ vector store, deferred) |
| **LLM extraction** | interpretive labels / taxonomy | **No** | API or local model | none | Yes (deep) | High | Medium |
| **Taxonomy** | fixed categories | Full (rule/classifier) | stdlib + a curated scheme | needs the taxonomy | Partial (human-designed) | High | None–Low |

## Pros and cons

- **TF-IDF** — *Pro:* deterministic, stdlib, well-understood; surfaces terms *distinctive* to
  a video against the channel's own corpus, which is exactly "what is this channel about."
  *Con:* bag-of-words, no phrases without n-grams, no meaning; IDF needs a corpus (the
  channel's videos for within-channel, a background set for cross-channel); sensitive to
  tokenization and stopwords.
- **RAKE** — *Pro:* deterministic, stdlib-viable, per-document (no corpus), and yields
  multi-word **keyphrases** from titles/transcripts cheaply. *Con:* noisy on long transcripts;
  phrase quality varies; no semantic grouping; results are per-document, so rolling up to a
  channel view is extra work.
- **YAKE** — *Pro:* deterministic, single-document, language-independent, often higher
  keyphrase precision than RAKE; no training or corpus. *Con:* costs a **dependency** (NLTK +
  spaCy via `pke`, or the `yake` package) — which triggers a full evaluation + ADR — for a
  result still lexical, not semantic.
- **Embeddings** — *Pro:* genuine **semantic** similarity; the only option that directly
  enables Q5 **clustering** and strong cross-channel comparison. *Con:* heavy — PyTorch +
  sentence-transformers, or a lighter Model2Vec path; a vector store (Chroma) that we have
  already deferred; deterministic only against a pinned model, so reproducibility is
  version-fragile. This is a stack decision, not a metric.
- **LLM extraction** — *Pro:* highest quality and flexibility; can produce a labeled
  taxonomy and handle nuance. *Con:* **non-deterministic**, networked, costs money, and by
  ADR-006 it **belongs in the Analysis layer, not the Derived layer** — an LLM topic label is
  an interpretation, not a reproducible fact. Also cuts against "LLMs only for what Python
  can't do deterministically" when cheaper lexical methods would answer Q4.
- **Taxonomy** — *Pro:* deterministic, stable, and the most **comparable across channels** —
  fixed categories are the natural axis for `compare-channels`. *Con:* someone must build and
  maintain the scheme; it is rigid and blind to novel or emergent topics; upfront curation
  cost with no guarantee it fits creator content.

## Benchmarks / evidence

**No benchmark has been run** — this is a research comparison, and no dependency is installed.
What is established from primary sources: RAKE and YAKE are single-document and need no corpus
or training; YAKE requires a dependency, while RAKE has stdlib-viable pure-Python
implementations; KeyBERT relies on sentence-transformers (PyTorch) for quality, with a lighter
Model2Vec path; TF-IDF is standard IR and stdlib-implementable.

The missing evidence is the decisive one: **how each method performs on our actual corpus**
(YouTube titles + auto-captions) judged against a small human-labeled topic set. That spike —
not more reading — is what should precede any choice. It is named in Next actions.

## Prior art / community feedback

- **RAKE** — Rose et al., *Automatic keyword extraction from individual documents* (2010).
  Pure-Python: [katchke/RAKE](https://github.com/katchke/RAKE); NLTK-based:
  [rake-nltk](https://pypi.org/project/rake-nltk/).
- **YAKE** — Campos et al.; reference implementation
  [LIAAD/yake](https://github.com/LIAAD/yake); available via `pke` and `textacy`.
- **Embeddings / KeyBERT** — [MaartenGr/KeyBERT](https://github.com/MaartenGr/KeyBERT) over
  [sentence-transformers](https://sbert.net); default model `all-MiniLM-L6-v2`.
- **TF-IDF** — classical information retrieval; `scikit-learn`'s `TfidfVectorizer` is the
  common off-the-shelf form.
- **Taxonomy** — YouTube's own category metadata (already captured per
  [001-youtube-intelligence.md](../modules/001-youtube-intelligence.md)) is a ready-made
  coarse taxonomy; finer schemes would be curated.

## Recommendation

**No winner is selected — by design, and because the decision is genuinely open.** What this
RFC does recommend is the *frame* for making it, stated as conditions (per the research
standard: "it depends" only with the conditions spelled out):

- **If the near-term need is Q4 alone** (dominant topics, descriptive, deterministic,
  stdlib) → the viable candidates are **TF-IDF over n-grams** and **RAKE**. Neither needs a
  dependency. Choose between them with a spike, not by argument.
- **If Q5 semantic clustering or cross-channel comparison is near-term** → **embeddings**
  become worth a formal dependency evaluation, which must also reopen the Chroma deferral.
  Not before.
- **If a stable, comparable category axis matters more than emergent topics** → **taxonomy**,
  starting from the YouTube categories we already store.
- **YAKE** competes with RAKE but costs a dependency; adopt only if a spike shows materially
  better keyphrases than stdlib RAKE.
- **LLM extraction** is not a Derived-layer option. Consider it only later, as an Analysis
  synthesis pass *over* deterministic topics — never as the topic metric itself.

Two hard constraints on whoever enacts this:

1. **This RFC authorizes no dependency.** YAKE, embeddings, and LLM each require their own
   evaluation and ADR first.
2. **Method and shape are decided together.** The enacting ADR must state both how topics are
   extracted *and* whether they are a structured channel-scope metric or a separate derived
   component — the shape question ADR-006 left open.

**Confidence: Medium.** The algorithmic properties are well-established (high confidence), but
no test on our real corpus has been run, and "best" depends on scope decisions not yet taken.
This would be wrong if our titles/captions turn out too sparse for lexical methods to separate
topics — which only the spike will reveal.

## Sources

All accessed 2026-07-11:

- [katchke/RAKE](https://github.com/katchke/RAKE) — pure-Python RAKE (stdlib-viable).
- [rake-nltk (PyPI)](https://pypi.org/project/rake-nltk/) — RAKE with NLTK stopwords.
- [LIAAD/yake](https://github.com/LIAAD/yake) — YAKE reference implementation; single-document,
  unsupervised, no corpus.
- [MaartenGr/KeyBERT](https://github.com/MaartenGr/KeyBERT) and
  [sentence-transformers](https://sbert.net) — embedding-based extraction; PyTorch dependency,
  `all-MiniLM-L6-v2` default, lighter Model2Vec path.
- Internal: [002-channel-intelligence.md](../modules/002-channel-intelligence.md) (Q4–Q6),
  [ADR-006](../decisions/adr-006-raw-derived-analysis.md) (Raw → Derived → Analysis),
  [chroma.md](../../research/technology/chroma.md) (vector store deferral).

## Open questions

- **Shape.** Structured channel-scope metric vs a separate derived component — decided with
  the method, in the enacting ADR.
- **Corpus for IDF.** For TF-IDF, is the channel's own videos enough (within-channel
  distinctiveness), or is a background corpus needed (and where from)?
- **Titles vs transcripts.** How to weight a 6-word title against a 3,000-word transcript so
  the transcript does not drown the title signal.
- **Evaluation set.** We have no labeled topics. A small hand-labeled sample is required to
  judge any method honestly.

## Next actions

- **Run a spike:** TF-IDF (n-grams) vs RAKE on the real `Marques Brownlee` corpus, judged
  against a small human-labeled topic set. Stdlib only, throwaway, no dependency. This
  precedes any method choice.
- **Gate every dependency:** YAKE / embeddings / LLM each need a `research/technology/`
  evaluation + ADR before adoption; none is authorized by this RFC.
- **Decide method + shape together** in the enacting ADR once the spike reports.
- Keep Q4–Q6 out of the intelligence module until then.
