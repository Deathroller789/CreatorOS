# DuckDB

## Summary

**Status: Candidate — not yet evaluated.** DuckDB is an embedded, in-process analytical
(OLAP) database — informally "SQLite for analytics." It is a potential complement to
SQLite for fast aggregate queries over collected data (e.g. analyzing large volumes of
comments, transcripts, or metrics), not a replacement for our source of truth.

A full evaluation is deliberately deferred until we have a concrete analytical workload;
evaluating it now would produce a decision on stale, hypothetical requirements.

## Evidence

_Pending full evaluation._

## Confidence

Not yet assessed.

## Sources

_To be gathered at evaluation time (primary: duckdb.org)._

## Open Questions

- Do our analytical needs actually exceed what SQLite handles comfortably?
- Would it read directly from the SQLite source of truth, or from exported files?

## Next Actions

- **Evaluate when** we first hit a reporting/analytics query that is slow or awkward in
  SQLite. Follow the [research standard](../../docs/standards/research.md) and record the
  outcome here.
