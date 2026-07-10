# Supabase

## Summary

**Status: Candidate — not yet evaluated.** Supabase is a hosted backend built on
PostgreSQL (managed Postgres plus auth, storage, realtime, and edge functions). It is a
potential option *if and when* CreatorOS needs multi-device sync, remote access, or a
shared/hosted database — none of which are near-term goals.

A full evaluation is deferred: adopting a hosted service is a significant, hard-to-reverse
dependency (data location, cost, lock-in) and must be judged against real requirements,
not anticipated ones. It would sit above SQLite, not replace it as the local source of
truth, unless a deliberate decision says otherwise.

## Evidence

_Pending full evaluation._

## Confidence

Not yet assessed.

## Sources

_To be gathered at evaluation time (primary: supabase.com, postgresql.org)._

## Open Questions

- Is a hosted/remote database actually required, or is local-first sufficient?
- Cost, data ownership, and exit strategy (avoiding lock-in) must be part of the
  evaluation.
- Relationship to the SQLite source of truth: sync target? replacement? read replica?

## Next Actions

- **Evaluate when** a requirement for remote access, multi-device sync, or collaboration
  is concrete. Compare against self-hosted Postgres and "local SQLite + sync" before
  committing.
