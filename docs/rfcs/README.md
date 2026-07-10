# Requests for Comments (RFCs)

An RFC proposes a decision that has **not been made yet** and opens it for discussion. It
is the counterpart to an [ADR](../decisions/) (a decision already made). RFCs exist to
prevent premature decisions on significant or contested choices — the practice large
engineering organizations use for a reason.

## RFC vs. ADR

- **RFC** — decision *pending*. A proposal with evidence and a recommendation, open for
  comment.
- **ADR** — decision *made*. Recorded in [`docs/decisions/`](../decisions/).

Lifecycle: research (`research/`) → **RFC** (Proposed → discussed → Accepted/Rejected) →
if accepted, an **ADR** enacts it. Not every decision needs an RFC — small or clear ones
go straight to an ADR. Use an RFC when the choice is significant, hard to reverse, or
genuinely open (e.g. *"Should CreatorOS use DuckDB instead of SQLite?"*).

## Naming & status

`rfc-NNN-kebab-title.md`, numbered sequentially. Status: **Proposed / Accepted / Rejected
/ Superseded**. An accepted RFC links to the ADR that enacts it.

## Format

1. Title — `RFC-NNN: <question>?`
2. **Status** + date
3. **Context** — the problem, why it's open now
4. **Proposal**
5. **Pros**
6. **Cons**
7. **Benchmarks / evidence** (if any)
8. **Prior art / community feedback**
9. **Recommendation**

### Template

```markdown
# RFC-NNN: <question>?

- **Status:** Proposed
- **Date:** YYYY-MM-DD

## Context

## Proposal

## Pros

## Cons

## Benchmarks / evidence

## Prior art / community feedback

## Recommendation
```

## Index

| # | Title | Status |
|---|-------|--------|
| [RFC-001](rfc-001-topic-representation.md) | How should CreatorOS represent topics? | Proposed |

_RFCs are written for real, open decisions — never hypothetically._
