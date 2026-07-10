# ADR-003: Why stdlib `sqlite3` (no ORM)?

- **Status:** Accepted
- **Date:** 2026-07-10 (recorded retroactively; decision made during Sprint 2)

## Context

[ADR-001](0001-memory-architecture.md) made SQLite the single source of truth. That left an
open question: how do we talk to it? The `analyze-channel` slice needed persistence
immediately, and we chose Python's standard-library `sqlite3` with hand-written SQL. This
record documents that decision, confirmed by the
[reuse audit](../../research/technology/reuse_audit.md).

## Decision

Use the **standard library `sqlite3` module with plain SQL**. Do not adopt an ORM. The data
layer is a small amount of code we own.

## Alternatives

- **SQLAlchemy** — very mature and powerful, but adds a dependency plus boilerplate and
  indirection for a handful of tables.
- **SQLModel** — pleasant typed models (Pydantic + SQLAlchemy), but newer, pulls in two
  dependencies, and is optimized for web APIs we don't have.
- **peewee** — lighter ORM, still a dependency for little gain.
- **Flat files (JSON/CSV)** — no transactions, no queries; rejected in ADR-001.

## Tradeoffs

- **Gain:** zero dependencies; fully transparent SQL; nothing between us and the database;
  trivially inspectable and portable.
- **Give up:** model mapping, migration tooling, and typed query ergonomics. We hand-write
  schema and migrations.

## Consequences

- We own a small data layer (currently `creatoros/analyze.py`; to be consolidated in a
  refactor).
- Migrations will need a simple, explicit approach when the schema evolves.
- **Revisit trigger:** if relations/migrations become genuinely complex, or we need the
  same models across an API surface, re-evaluate SQLAlchemy or SQLModel.

## Exit strategy

**None needed.** `sqlite3` is standard library and the SQL is plain; the database is a
single portable file readable by any language or tool.
