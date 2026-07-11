# Architecture Decision Records (ADRs)

CreatorOS is an operating system, not a throwaway project. Every important decision gets
one record here, written **before** or **as** we act on it. Over time these ADRs become
the memory of CreatorOS — *why* it is the way it is. We write them so a choice can be
trusted, or overturned with evidence, a year from now.

## When an ADR is required

Write an ADR for any important, hard-to-reverse decision:

- adding a dependency, library, MCP server, or external tool,
- introducing a new service, storage engine, or data format,
- any architectural choice that shapes how the system is built.

Research (in `research/`) is *why we looked*; an ADR is *what we chose*. A research report
that leads to a binding choice gets an ADR that links back to it. When a decision is
significant but **not yet made**, it starts as an [RFC](../rfcs/) (open for comment) and
becomes an ADR once accepted.

## Naming

Going forward, ADRs are numbered Markdown files: `adr-NNN-kebab-title.md`
(e.g. `adr-002-why-yt-dlp.md`). Numbers are sequential and never reused.

> The existing record `0001-memory-architecture.md` predates this naming and is kept
> as-is for now.

## Format

Each ADR contains:

1. **Title** — `ADR-NNN: Why <X>?` (or the decision stated plainly).
2. **Status** — Proposed / Accepted / Superseded (link the superseding ADR).
3. **Context** — the problem and why we're deciding now.
4. **Decision** — what we chose, in one or two sentences.
5. **Alternatives** — the real options considered, each with why it lost.
6. **Tradeoffs** — what we gain and what we give up.
7. **Consequences** — what this makes easier/harder, and the **revisit trigger**.

Keep them short. A record that fits on one screen gets read; a 2,000-word one doesn't.

### Template

```markdown
# ADR-NNN: Why <X>?

- **Status:** Proposed
- **Date:** YYYY-MM-DD

## Context

## Decision

## Alternatives

## Tradeoffs

## Consequences
```

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-memory-architecture.md) | Memory architecture: SQLite as source of truth, Memory MCP disabled | Accepted |
| [ADR-002](adr-002-youtube-extraction-stack.md) | YouTube extraction stack (yt-dlp + youtube-transcript-api) | Accepted |
| [ADR-003](adr-003-why-stdlib-sqlite3-no-orm.md) | Why stdlib `sqlite3` (no ORM) | Accepted |
| [ADR-004](adr-004-why-argparse.md) | Why `argparse` (no CLI framework) | Accepted |
| [ADR-005](adr-005-why-playwright-library-not-mcp.md) | Why the Playwright library (not the MCP) | Accepted |
| [ADR-006](adr-006-raw-derived-analysis.md) | Raw → Derived → Analysis (the Derived Metrics Engine) | Accepted |
| [ADR-007](adr-007-report-export-command-surface.md) | The report export command surface (`export` + renderer registry) | Proposed |

_ADRs are authored when a decision is actually made, not before._
