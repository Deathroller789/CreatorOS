# 0001 — Memory architecture: SQLite as source of truth, Memory MCP disabled

- **Status:** Accepted (2026-07-10)
- **Deciders:** Repo owner

## Context

CreatorOS needs durable state — things the system knows and relies on across sessions.
During setup we installed the **Memory MCP** (`@modelcontextprotocol/server-memory`, a
file-backed knowledge graph) as one option for this.

Two concerns surfaced:

1. **Control.** The Memory MCP lets the assistant write to persistent memory
   automatically, as a side effect of conversation. For an operating system, state that
   changes implicitly is hard to audit, reason about, and trust.
2. **Authority.** If both an MCP knowledge graph and a real database hold state, it is
   ambiguous which one is correct. An OS needs exactly one source of truth.

## Options considered

### A. Memory MCP as the primary store
- **Pros:** zero schema work; assistant can persist facts directly.
- **Cons:** implicit/automatic writes; opaque graph format; not easily queried by other
  tools; another process to trust; unclear ownership of the data. Fails the "auditable,
  single source of truth" bar.

### B. SQLite as source of truth; no memory MCP
- **Pros:** explicit, inspectable, queryable by any tool/language; a single file that is
  trivially backed up; well-understood, zero-server, stable for decades; writes happen
  only through code we control.
- **Cons:** requires us to design a schema and write access code; assistant cannot
  "just remember" — it must go through the database.

### C. SQLite as source of truth; Memory MCP as an optional *cache* on top
- **Pros:** keeps the ergonomics of quick recall while SQLite stays authoritative.
- **Cons:** cache-invalidation complexity; only worth it once we feel real pain. Premature
  now.

## Decision

- **SQLite will be the source of truth** for CreatorOS state.
- **The Memory MCP is disabled now** — removed from `.mcp.json`; its data directory
  (`D:\Tools\mcp-memory`) was deleted. No memory was written before removal.
- Memory MCP is **not rejected forever**: it may return later strictly as a *cache* in
  front of SQLite (Option C), never as the database.

Adopting SQLite itself is a new dependency and gets **its own decision record** (schema,
migrations, and the still-open question of whether the live `.db` is committed to git or
treated as runtime state) before we write any code against it.

## Consequences

- **Easier:** one authoritative, inspectable store; no implicit background memory writes;
  any tool can read the data.
- **Harder:** no free-form "assistant remembers" until the SQLite layer exists; recall
  must be built deliberately.
- **Revisit trigger:** reopen this if (a) we adopt SQLite and repeatedly hit latency or
  ergonomics pain that a cache would fix, or (b) requirements change such that a graph
  store genuinely beats a relational one for our access patterns.
