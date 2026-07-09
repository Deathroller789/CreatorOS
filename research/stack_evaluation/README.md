# Stack Evaluation

Every technology we seriously consider gets one file here — a durable evaluation so we
**never research the same question twice**. This is the memory of *why* the stack looks
the way it does.

## What belongs here

One file per technology (`sqlite.md`, `duckdb.md`, `supabase.md`, `chroma.md`, …), named
lowercase per [naming](../../docs/standards/naming.md). A file exists as soon as a
technology is a real candidate, even before it's evaluated.

## Format

Each file follows the [research standard](../../docs/standards/research.md):
**Summary → Evidence → Confidence → Sources → Open Questions → Next Actions**.

Status is stated in the Summary as one of:

- **Candidate** — on our radar, not yet evaluated.
- **Evaluated — adopt** / **Evaluated — reject** / **Evaluated — hold** — decision made.

## Relationship to decision records

An evaluation here is the *research*. When it leads to a binding choice, that choice is
recorded as a numbered ADR in [`docs/decisions/`](../../docs/decisions/), which links back
here. Evaluation = why we looked; decision = what we chose.

## Index

| Technology | Role considered for | Status |
| --- | --- | --- |
| [sqlite](sqlite.md) | Primary state store (source of truth) | Evaluated — adopt |
| [duckdb](duckdb.md) | Analytical queries over collected data | Candidate |
| [supabase](supabase.md) | Hosted Postgres + backend services | Candidate |
| [chroma](chroma.md) | Vector store for embeddings/search | Candidate |
