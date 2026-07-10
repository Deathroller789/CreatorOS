# ADR-005: Why the Playwright library (not the Playwright MCP)?

- **Status:** Accepted
- **Date:** 2026-07-10 (recorded retroactively; Playwright adopted in Sprint 1, MCP question
  settled by the reuse audit)

## Context

CreatorOS needs browser automation for sources that require a real browser (JS-rendered
pages, future non-YouTube ingestion). Playwright was installed early. The
[reuse audit](../../research/technology/reuse_audit.md) then asked whether Microsoft's
official **Playwright MCP** server should replace direct library use.

## Decision

Use the **Playwright Python library, in-process**, wrapped behind our own interface. **Do
not adopt the Playwright MCP server.**

## Alternatives

- **Playwright MCP** (microsoft/playwright-mcp) — official and actively maintained, but
  aimed at interactive/agentic loops. It adds a server process and roughly 4× the token cost
  per task; Microsoft itself now steers coding agents toward the CLI/library. It solves a
  problem we don't have.
- **Selenium** — mature, but an older API with no advantage over Playwright.
- **requests + BeautifulSoup** — fine for static HTML, cannot render JS. Kept as the cheaper
  path when a browser isn't needed.
- **Crawl4AI** — built on Playwright; bundles crawling + LLM output we'd rather compose
  ourselves.

## Tradeoffs

- **Gain:** deterministic in-process control, no extra server to run, no token overhead,
  direct API access.
- **Give up:** the MCP's agent-friendly page introspection and persistent browsing state.
  We don't need those for programmatic ingestion.

## Consequences

- Browser binaries live outside the repo (`PLAYWRIGHT_BROWSERS_PATH=D:\Tools\playwright`).
- Browser use stays behind a thin wrapper so the engine can be swapped.
- **Revisit trigger:** if CreatorOS ever needs autonomous, exploratory agentic browsing
  (rather than scripted extraction), re-evaluate the Playwright MCP.

## Exit strategy

**Low–Medium.** The API is standard and Selenium is a mature substitute; only the
inherently browser-coupled flows would need rework. Nothing we persist depends on Playwright.
