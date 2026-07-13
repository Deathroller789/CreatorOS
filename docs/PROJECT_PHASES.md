# CreatorOS development phases

CreatorOS is built in deliberate phases.
Each phase has one job, and a phase does not end until that job is genuinely done — not when
the calendar says so.
This document records which phase we are in and what it means for what we build next.

## Phase 1 — Foundation (COMPLETED)

**Goal:** build the architecture, principles, and working intelligence pipeline that everything
later stands on — and stop there, before speculating about features.

Foundation is **complete**.
CreatorOS can ingest a real YouTube channel and produce descriptive, confidence-bounded
intelligence end-to-end, on a stack and a set of decisions designed to be trusted a year from
now.

What Foundation delivered:

| Area | What exists | Where |
|------|-------------|-------|
| Architecture | Raw → Metrics → Intelligence → Reporting → Knowledge; each layer knows only the one below; Knowledge a sibling of Reporting | [PROJECT_VISION.md](PROJECT_VISION.md), [ENGINEERING.md](ENGINEERING.md) |
| Engineering principles | Reuse first, build only the intelligence layer, stdlib-first, maintainability over speed, no dependency without an evaluation | [ENGINEERING.md](ENGINEERING.md) |
| Standards | Python, markdown, naming, folders, research — all binding | [docs/standards/](standards/) |
| ADRs | Ten accepted/recorded decisions (memory, extraction stack, sqlite/no-ORM, argparse, Playwright, raw→derived, export surface, versioning, error philosophy, persistence) | [docs/decisions/](decisions/) |
| RFC system | Decisions-not-yet-made open for comment before they become ADRs | [docs/rfcs/](rfcs/) |
| Metrics engine | Registry of pure, composable, age-normalizing metric functions; computed on read, never stored; never touches SQLite | [creatoros/metrics/](../creatoros/metrics/), [ADR-006](decisions/adr-006-raw-derived-analysis.md) |
| Intelligence engine | Descriptive, ranking-based, confidence-bounded findings (outliers, titles, cadence) behind the immutable `ChannelFindings` contract | [creatoros/intelligence/](../creatoros/intelligence/), [Module 002](modules/002-channel-intelligence.md) |
| Reporting layer | Deterministic renderers that serialize findings only — never compute, infer, or reorder | [creatoros/reporting/](../creatoros/reporting/) |
| Renderer architecture | Markdown + JSON renderers, golden-file regression, JSON as canonical exchange | [ADR-007](decisions/adr-007-report-export-command-surface.md) |
| Versioning philosophy | One human-facing SemVer package version; independent monotonic schema versions per contract | [ADR-008](decisions/adr-008-versioning-strategy.md) |
| Error philosophy | Conditions vs responses vs outcomes; exit codes `0`/`1`/`2`; error provenance; unavailable vs missing | [ADR-009](decisions/adr-009-error-philosophy.md) |
| Persistence philosophy | Persist captures, recompute derivations; preserve history, never avoid computation; one-way dependency direction | [ADR-010](decisions/adr-010-persistence-strategy.md) |

**Architecture is now frozen.**
No new ADRs, no new infrastructure, and no speculative engineering during the next phase.
The architecture changes again only if real usage proves an existing ADR *wrong* — not because
a new idea sounds good.

## Phase 2 — Real-world usage (CURRENT)

**Goal:** use CreatorOS on a large number of real YouTube channels and let reality — not
speculation — define what gets built next.

The rule for this phase is strict:

> **Do not build features unless repeated real usage demonstrates the need.**

The *output* of this phase is not code.
It is **GitHub issues, observations, and product insights** drawn from actually running the
tool.
Every friction becomes an issue; every *repeated* pain becomes candidate future product work.
Roadmap items are not invented here — they are discovered.

### How to run this phase

1. Analyze real channels with `creatoros analyze-channel <url>`, across varied niches and sizes.
2. After each analysis, work through the
   [channel analysis checklist](usage/CHANNEL_ANALYSIS_CHECKLIST.md).
3. Turn every friction into a GitHub issue, labelled bug / enhancement / research.
4. Watch for *repetition*: a pain felt once is noise; a pain felt across many channels is signal.

### Suggested coverage

Breadth across niches matters more than any single number — different niches stress the
intelligence differently (upload cadence, title conventions, view distributions all vary).

| Niche | Suggested channels |
|-------|--------------------|
| Horror | 100 |
| Finance | 50 |
| Tech | 50 |
| Education | 50 |

### What this phase must not do

- **Do not invent roadmap items.** If usage did not surface it, it is not a Phase 2 output.
- **Do not build infrastructure.** The pending backlog (export command, findings persistence,
  retry-with-backoff) waits until usage demonstrates the need.
- **Do not write new ADRs.** Architecture is frozen; an ADR is revisited only if usage proves it
  incorrect.

## Phase transitions

A phase ends when its job is done, and the transition is recorded here.

| Phase | Status | Ends when |
|-------|--------|-----------|
| 1 — Foundation | **COMPLETED** | The architecture and a working end-to-end intelligence pipeline exist and are documented. |
| 2 — Real-world usage | **CURRENT** | Enough real usage has accumulated that a genuine, evidence-backed roadmap emerges from the issues filed. |
| 3 — Evidence-led product | Not started | Defined by what Phase 2 discovers — deliberately not specified in advance. |
