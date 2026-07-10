# Chroma

## Summary

**Status: Candidate — not yet evaluated.** Chroma is an open-source vector database for
storing and querying embeddings (semantic search, retrieval). It is a potential option for
when CreatorOS needs similarity search over transcripts, comments, or notes. The main
alternative is keeping vectors inside SQLite via the `sqlite-vec` extension, which would
preserve our single-source-of-truth model.

A full evaluation is deferred until an embedding/search feature is actually scoped.

## Evidence

_Pending full evaluation._

## Confidence

Not yet assessed.

## Sources

_To be gathered at evaluation time (primary: trychroma.com, and `sqlite-vec` docs for the
in-file alternative)._

## Open Questions

- Does a separate vector store earn its keep, or does `sqlite-vec` in the existing SQLite
  file cover our needs with less operational surface?
- Embedding model, dimensionality, and volume — unknown until a feature needs them.

## Next Actions

- **Evaluate when** the first semantic-search / retrieval feature is scoped. Explicitly
  compare Chroma against `sqlite-vec` (see [sqlite](sqlite.md)) so we don't add a second
  data store without cause.
