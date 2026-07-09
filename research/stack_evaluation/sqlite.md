# SQLite

## Summary

**Recommendation: adopt SQLite as the single source of truth for CreatorOS state.**
(Evaluated 2026-07-10.) SQLite is an embedded, zero-configuration, single-file relational
database with full ACID guarantees and an exceptionally stable, long-supported file
format. It matches our core requirement — one authoritative, inspectable, queryable store
with no server to operate — better than any alternative considered. Confidence: **High**.

## Evidence

- **Embedded & zero-ops.** Runs in-process; no server, no daemon, no network. The entire
  database is one file that is trivial to back up, copy, inspect, and version.
- **ACID / reliable.** Fully transactional. In WAL mode it supports one writer with many
  concurrent readers — sufficient for a local-first creator OS.
- **Auditable & portable.** Any tool in any language can open the file; the schema and
  data are inspectable with the `sqlite3` CLI. This directly serves our "single, auditable
  source of truth" goal (see `docs/decisions/0001-memory-architecture.md`).
- **Longevity.** SQLite is one of the most widely deployed pieces of software in the
  world and its developers commit to supporting the file format long-term (through 2050).
  A decision to store data in SQLite is safe to make for a system meant to last.
- **Speed for our workload.** For local, mostly-single-writer read-heavy access, SQLite is
  fast and has no network round-trips.
- **Extensible when needed.** Vector search (`sqlite-vec`), full-text search (FTS5), and
  JSON support are available without leaving the file.

Where it is *not* the right tool: heavy multi-writer concurrency, distributed/multi-node
access, or large-scale analytical scans across huge datasets — those point to Postgres
(Supabase) or DuckDB respectively, layered *on top of* SQLite as the source of truth, not
replacing it.

## Confidence

**High.** SQLite's properties are stable and well-documented, and our access pattern
(local, single-writer, read-heavy, durability-critical) is squarely in its sweet spot.
This would only be wrong if CreatorOS grows into a concurrent multi-writer or distributed
system, which is explicitly not a near-term goal.

## Sources

- SQLite — Appropriate Uses For SQLite: <https://www.sqlite.org/whentouse.html> (accessed 2026-07-10)
- SQLite — Write-Ahead Logging: <https://www.sqlite.org/wal.html> (accessed 2026-07-10)
- SQLite — Long Term Support: <https://www.sqlite.org/lts.html> (accessed 2026-07-10)

## Open Questions

- Is the live `.db` committed to git (versioned source of truth) or treated as runtime
  state with only schema/migrations tracked? **To be decided in the SQLite ADR.**
- Migration tooling: plain SQL migration files vs. a library. Prefer the simplest thing
  that is reproducible.
- Vector search: `sqlite-vec` in-file vs. a dedicated store (see [chroma](chroma.md)).
  Defer until embeddings are actually needed.

## Next Actions

- Write `docs/decisions/0002-*.md` adopting SQLite, resolving schema layout, migration
  approach, and the commit-the-`.db` question, before any database code is written.
- Re-evaluate `sqlite-vec` vs. Chroma when the first embedding/search feature is scoped.
