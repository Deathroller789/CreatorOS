# Reuse Audit — CreatorOS Infrastructure

## Summary

**Evaluated 2026-07-10 (issue #7).** Recommendation: CreatorOS should be built almost
entirely from the **standard library plus a small set of mature, permissively-licensed
libraries**, with **zero frameworks**. We build only the *intelligence layer* (research
workflow, analysis, pattern detection, synthesis, decisions) and thin wrappers around
reused extraction/storage software. Confidence: **High**.

The recommended minimal stack (details below):

| Capability | Choice | Decision | Why (one line) |
| --- | --- | --- | --- |
| YouTube metadata/comments/thumbnails/subs | **yt-dlp** (library) | Adopt + Wrap | Widest coverage, no key, maintained daily; in-process |
| YouTube transcripts | **youtube-transcript-api** | Adopt + Wrap | Purpose-built, clean timed text, no key |
| Browser automation | **Playwright** (Python lib) | Adopt + Wrap | Dominant, reliable; library beats the MCP for our use |
| Article/web-page text (future) | **Trafilatura** | Adopt when needed | Best extraction accuracy, tiny, widely used |
| Source of truth | **stdlib `sqlite3`** | Adopt (thin code) | Zero deps, single file; ORM adds boilerplate we don't need |
| LLM access (intelligence layer) | **Anthropic SDK** (direct) | Adopt when needed + Wrap | Single-loop agent needs no framework |
| CLI | **stdlib `argparse`** | Keep | Zero deps; already in use |
| Config | **stdlib (`tomllib` + env)** | Keep | No dep until proven necessary |
| Scheduling/automation | **GitHub Actions / OS cron** | Adopt | No runtime dependency |
| Package/lint/test | **uv · Ruff · stdlib `unittest`** | Settled | Already adopted; minimal |

**What we explicitly do NOT adopt:** LangChain / LlamaIndex / CrewAI, any ORM
(SQLAlchemy / SQLModel), Typer / Click, a YouTube MCP server, Crawl4AI, and (for now)
DuckDB / Chroma. Each is justified below. Net effect: the stack stays small and most of
CreatorOS is our own intelligence code, not plumbing.

## Method

For each capability we searched GitHub, the MCP ecosystem, official SDKs/APIs, and mature
OSS, and judged on engineering quality — maturity, maintenance, adoption, license, API
quality, extensibility, docs, sustainability, risk — **not popularity**. Where two
options are comparable, we prefer the one that **removes the most code from CreatorOS**.

## Capability audit

### 1. YouTube extraction (metadata, comments, thumbnails, subtitles)

| Option | Maturity / maintenance | License | Notes |
| --- | --- | --- | --- |
| **yt-dlp** (library) | Very high; ~daily releases | Unlicense | Widest coverage; in-process; already adopted (ADR-002) |
| YouTube Data API v3 | Official, stable | Google ToS | Authoritative counts, but API key + quota |
| YouTube MCP servers (anaisbetts/mcp-youtube, jkawamoto/…, kevinwatt/yt-dlp-mcp) | Mixed; small teams | MIT (varies) | **All wrap yt-dlp/youtube-transcript-api anyway** |
| pytubefix / scrapetube | Active but narrower | Unlicense/MIT | Thinner than yt-dlp |

**Decision: Adopt `yt-dlp` as a library + Wrap it behind a thin `tools/youtube/` interface.
Ignore the YouTube MCP servers.** An MCP here would wrap the *same* library we already
use, but add a running server process, weaker control, and dependence on a small
third-party's maintenance — that is *more* moving parts, not less code. Data API v3 stays
the documented fallback for authoritative counts.

### 2. YouTube transcripts

**Decision: Adopt `youtube-transcript-api` + Wrap.** Purpose-built, returns clean timed
segments, no key/browser, active (v1.2.4, Jan 2026), MIT. Already adopted (ADR-002).

### 3. Browser automation (JS-heavy pages, future ingestion)

| Option | Maturity / maintenance | License | Notes |
| --- | --- | --- | --- |
| **Playwright** (Python library) | Dominant in 2026; active | Apache-2.0 | Reliable accessibility APIs; already installed |
| Playwright **MCP** (microsoft/playwright-mcp) | Official, weekly updates | Apache-2.0 | Great for agentic *test* loops; ~4× the tokens; Microsoft now steers coding agents to CLI/library |
| Selenium | Mature but heavier/older API | Apache-2.0 | No advantage over Playwright |

**Decision: Adopt the Playwright library + Wrap. Ignore the Playwright MCP** (for now) —
it targets interactive agent/test loops and adds token + server overhead; programmatic
in-process control is simpler and cheaper for CreatorOS. (Playwright adoption deserves a
short backfill ADR — it's a real, made decision.)

### 4. Article / web-page text extraction (future: websites, newsletters)

| Option | Maturity / maintenance | License | Notes |
| --- | --- | --- | --- |
| **Trafilatura** | Very high; benchmark leader (F1 ~0.945); used by HF/IBM/Stanford | Apache-2.0 *(confirm)* | Tiny, focused; text + metadata |
| readability-lxml | Stable | Apache-2.0 | Simpler, less accurate |
| Crawl4AI | Very active, huge adoption | Apache-2.0 | Built on Playwright + asyncio; LLM-oriented but heavy — overlaps tools we'd already have |
| Newspaper3k/4k | Aging | MIT | Narrower |

**Decision (when the need is real): Adopt `Trafilatura` for static article text; escalate
to the Playwright wrapper only for JS-rendered pages. Ignore Crawl4AI** (its value is
LLM-output + crawling we can compose from Trafilatura + Playwright + our own intelligence
layer). Deferred until a non-YouTube source is actually scoped.

### 5. Source of truth (SQLite access layer)

| Option | Maturity | License | Notes |
| --- | --- | --- | --- |
| **stdlib `sqlite3`** | Highest | PSF | Zero deps; enough for our schema |
| SQLAlchemy | Very high | MIT | Powerful, but boilerplate + dependency |
| SQLModel | Newer | MIT | Pydantic+SQLAlchemy; nice for web APIs, not our case |

**Decision: Keep stdlib `sqlite3`; build the (small) data layer ourselves. Ignore ORMs.**
An ORM adds a dependency and indirection for a handful of tables. Revisit only if
relations/migrations become genuinely complex. This *is* "wrap existing software" — SQLite
is the software; the thin Python is ours.

### 6. Analytics (DuckDB) & 7. Vector search / RAG (Chroma / sqlite-vec)

**Decision: Ignore for now (candidates).** No current workload needs them. When analytics
arrive, evaluate DuckDB against SQLite; when semantic search arrives, prefer `sqlite-vec`
(keeps the single-store model) over a separate Chroma server unless proven necessary. See
`duckdb.md`, `chroma.md`.

### 8. LLM access & agent orchestration (the intelligence layer's plumbing)

| Option | Maturity | License | Notes |
| --- | --- | --- | --- |
| **Anthropic SDK** (direct) | Official, stable | MIT | Direct tool-use/streaming/caching; explicit loop |
| LangChain / LangGraph | Very high adoption | MIT | Abstraction tax; value is its 200+ integrations, which we don't need |
| LlamaIndex / CrewAI | Active | MIT/Apache | Framework overhead for multi-agent/RAG we don't have |

**Decision: Adopt the Anthropic SDK directly + Wrap a thin `llm` helper, when intelligence
features begin. Ignore LangChain/LlamaIndex/CrewAI.** CreatorOS is single-loop reasoning;
the provider SDK is the lightest thing that works. This is where we *build*, but even here
we reuse the SDK rather than hand-rolling HTTP. (Gets an ADR at adoption.)

### 9–12. CLI, config, scheduling, dev tooling

- **CLI → stdlib `argparse` (keep).** Ignore Typer/Click: they add dependencies for
  ergonomics we don't yet need. Reconsider Typer only if the CLI grows many commands.
- **Config → stdlib `tomllib` + environment variables.** Ignore `pydantic-settings` until
  configuration is non-trivial.
- **Scheduling/automation → GitHub Actions (cloud) or OS cron (local).** Ignore
  APScheduler/Celery — no runtime dependency or broker needed.
- **Dev tooling → uv, Ruff, stdlib `unittest` — settled** and already minimal.

## Net effect on codebase size

The stack is stdlib + ~4 runtime libraries in active use (yt-dlp, youtube-transcript-api,
Playwright) plus the Anthropic SDK later. No frameworks, no ORM, no MCP servers to operate.
Every "reuse" choice above removes code or dependencies we would otherwise carry. The
intended trajectory holds: **CreatorOS's own code should be mostly intelligence, and should
shrink or stay flat as reused software absorbs the undifferentiated work.**

## Confidence

**High.** The extraction/automation choices are already validated in production (Sprint 2)
and by external benchmarks/maintenance data; the "no framework / no ORM / stdlib CLI"
calls follow directly from the minimalism principle and current (2026) practitioner
consensus. Main uncertainty is future-facing (article extraction, analytics, vectors,
LLM), which we deliberately defer rather than decide early.

## Sources

- Playwright MCP — <https://github.com/microsoft/playwright-mcp>, <https://playwright.dev/docs/getting-started-mcp> (accessed 2026-07-10)
- Trafilatura — <https://github.com/adbar/trafilatura>; extraction-tool comparison <https://www.firecrawl.dev/blog/best-web-extraction-tools> (accessed 2026-07-10)
- Anthropic SDK vs LangChain — <https://docs.langchain.com/oss/python/deepagents/comparison>, <https://mooreiq.ai/blog/claude-agent-anthropic-sdk-vs-langchain> (accessed 2026-07-10)
- CLI comparison — <https://typer.tiangolo.com/alternatives/>, <https://codecut.ai/comparing-python-command-line-interface-tools-argparse-click-and-typer/> (accessed 2026-07-10)
- SQLite vs ORM — <https://www.thenerdnook.io/p/sqlite-vs-sqlalchemy> (accessed 2026-07-10)
- YouTube MCP servers — <https://www.ekamoira.com/blog/youtube-mcp-server-comparison-2026-which-one-should-you-use>, <https://github.com/anaisbetts/mcp-youtube> (accessed 2026-07-10)

## Open Questions

- Trafilatura's exact license at adoption time (Apache-2.0 expected) — confirm before use.
- When intelligence features start, does a single Anthropic SDK wrapper suffice, or do we
  need light multi-step orchestration? Revisit only if we feel real pain.
- Article extraction only becomes concrete once a non-YouTube source is scoped.

## Next Actions

- Proceed with the current stack; no new installs from this audit.
- Backfill short ADRs for the real, already-made decisions: **Why yt-dlp** (exists as
  ADR-002), **Why Playwright**, **Why stdlib sqlite3 / no ORM**, **Why argparse / no CLI
  framework** — so the reasoning is recorded per ENGINEERING.md principle 6.
- When refactoring post-MVP, consolidate YouTube extraction behind a thin `tools/youtube/`
  wrapper (single seam) so the underlying library can be swapped without touching the
  intelligence layer.
- Unblocks **#2 (comments)**: build on `yt-dlp` (`getcomments`), not a new dependency.
