# Decision Records

CreatorOS is an operating system, not a throwaway project. Every choice should still
make sense a year from now. To keep that honest, **we write decisions down before we
act on them.**

## When a record is required

Write a decision record **before** you:

- add a dependency or library,
- install an MCP server or external tool,
- introduce a new service, storage engine, or data format, or
- make any architectural choice that is hard to reverse.

If you're only removing/downgrading something, a short record is still worth it so the
reasoning isn't lost.

## Format

Records are numbered Markdown files: `NNNN-short-title.md`. Each contains:

1. **Status** — Proposed / Accepted / Superseded (link the superseding record).
2. **Context** — the problem, and why we're deciding now.
3. **Options considered** — at least two real alternatives, each with tradeoffs.
4. **Decision** — what we chose.
5. **Consequences** — what this makes easy, what it makes harder, and the
   **revisit trigger** (the condition under which we'd reopen this).

Keep them short. A record that fits on one screen gets read; a 2,000-word one doesn't.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-memory-architecture.md) | Memory architecture: SQLite as source of truth, Memory MCP disabled | Accepted |
