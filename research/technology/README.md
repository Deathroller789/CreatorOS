# Technology Research

Evaluations of technologies, libraries, and tools we consider for CreatorOS. One file per
subject, so we **never research the same question twice**. This is the memory of *why* the
stack looks the way it does.

## What belongs here

One file per technology or library (`sqlite.md`, `duckdb.md`, `youtube_library_evaluation.md`,
…), named lowercase per [naming](../../docs/standards/naming.md). A file exists as soon as a
subject is a real candidate, even before it's evaluated.

## Format

Each file follows the [research standard](../../docs/standards/research.md):
**Summary → Evidence → Confidence → Sources → Open Questions → Next Actions**.

Status is stated in the Summary as one of:

- **Candidate** — on our radar, not yet evaluated.
- **Evaluated — adopt** / **Evaluated — reject** / **Evaluated — hold** — decision made.

## Relationship to decision records

An evaluation here is the *research*. When it leads to a binding choice, that choice is
recorded as an ADR in [`docs/decisions/`](../../docs/decisions/), which links back here.
Evaluation = why we looked; decision = what we chose.

## Index

### Cross-cutting

| Subject | Role | Status |
| --- | --- | --- |
| [reuse_audit](reuse_audit.md) | Whole-stack reuse audit — the minimal maintainable stack (issue #7) | Complete |

### Data layer / stack

| Technology | Role considered for | Status |
| --- | --- | --- |
| [sqlite](sqlite.md) | Primary state store (source of truth) | Evaluated — adopt |
| [duckdb](duckdb.md) | Analytical queries over collected data | Candidate |
| [supabase](supabase.md) | Hosted Postgres + backend services | Candidate |
| [chroma](chroma.md) | Vector store for embeddings/search | Candidate |

### Libraries / tools

| Subject | Role | Status |
| --- | --- | --- |
| [youtube_library_evaluation](youtube_library_evaluation.md) | YouTube data extraction | Evaluated — yt-dlp + youtube-transcript-api |
