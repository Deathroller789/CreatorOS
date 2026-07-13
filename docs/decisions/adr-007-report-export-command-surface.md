# ADR-007: The report export command surface

- **Status:** Accepted
- **Date:** 2026-07-12

## Context

The reporting layer can turn one `ChannelFindings` into more than one format: Markdown
today, JSON today, and — by design — HTML, PDF, and others later. Every one of them is a
`Renderer` (`render(findings, metadata) -> str`); adding a format is meant to touch
neither the intelligence layer nor the findings contract.

`analyze-channel` already renders the default Markdown report as the last step of the
ingest pipeline. What is missing is a way to render an **already-ingested** channel into
**any** format without re-ingesting — the thing a creator does when they want the same
analysis as a PDF to email, or as JSON to feed another tool. The instruction for this work
was explicit: *do not attach export to `analyze`; it should consume canonical findings and
render any supported format; decide the surface with future HTML/PDF/dashboard renderers
in mind, not just today's two formats.*

So the decision is the **command surface**, before any code: what the command is called,
what it takes, and how it grows. Getting this wrong is expensive — a CLI verb is a public
contract that scripts and habits form around.

## Decision

A single command, backed by a **renderer registry**:

```
creatoros export <channel> --format <fmt> [--output PATH]
```

- **One verb, `export`, format-agnostic.** Not one verb per format, and not a separate
  `render` verb for "presentation" formats. `--format` selects a renderer.
- **Formats come from an explicit registry**, exactly as metrics do (ADR-006): each
  renderer self-registers, the active ones are imported by hand in a one-line list, and
  the CLI enumerates `--format` choices from the registry. Adding HTML is "write and
  register `HtmlRenderer`" — the CLI, the intelligence layer, and the findings contract do
  not change. `export --list-formats` prints what is available.
- **Input is canonical findings, never a rendered report.** Today `<channel>` is a stored
  `channel_id` or handle, and findings are recomputed from SQLite via `analyze_channel`
  (no network; deterministic given `now`). When the knowledge layer (#33) persists
  findings, a `--from-findings <path.json>` input is added that renders straight from a
  stored findings document. HTML is never produced by parsing Markdown — both come from
  findings. This keeps "never parse rendered reports" true by construction.
- **`export` never ingests.** Ingestion is network-bound and mutating; rendering is
  offline, cheap, and repeatable across formats. Keeping them separate commands is the
  point — it is why export is not a flag on `analyze`.

**A renderer serializes, and only serializes.** Its sole responsibility is to turn a
`ChannelFindings` and its metadata into bytes in one target format. It never computes a
metric, infers or enriches a value, reorders, filters, or drops findings, or modifies the
contract in any way — the findings it is handed are exactly the findings it serializes.
Any format-specific rounding or layout is presentation, not a change to a fact. Anything
that creates or alters a fact is intelligence and lives upstream, never in a renderer.
This invariant is what lets one findings object fan out to many formats and stay
comparable across all of them (the #29 regression guard depends on it).

The exchange-vs-presentation distinction (JSON is the canonical exchange format; Markdown,
HTML, and PDF are disposable presentation) is preserved as a property **of the format**,
documented and enforced by JSON's versioned schema — not by the command verb. One command
can emit both because, to the reporting layer, they are peer renderers.

## Alternatives

### The verb: `export` vs `render` vs `report`

| Verb | For it | Against it |
|------|--------|-----------|
| **`export`** (chosen) | Dominant CLI convention for "produce an artifact from internal state"; reads acceptably for every format ("export as PDF / HTML / JSON"); the project's own earlier framing already called JSON "the canonical export". | Faint data-dump connotation, slightly odd for a styled PDF. |
| `render` | Most accurate to the code — every format is a `Renderer`, so "render to HTML" is literally true. | Leaks an internal abstraction name into the public UX; "render to json" reads oddly to a creator; keep `Renderer` an implementation term, not a command. |
| `report` | Domain-native (CreatorOS produces reports); neutral across data and presentation. | Weak as a verb; collides conceptually with the noun "report" that the command *writes*, inviting `report report ...` confusion. |

`export` wins on convention and readability; `Renderer` stays the internal name.

### Two verbs — `export` (exchange) and `render` (presentation)

Tempting, because it stamps the "JSON is exchange, Markdown is presentation" principle
directly onto the UX. Rejected: it forces every future format to be pre-classified as
exchange or presentation (is CSV exchange? is a human-readable JSON both?), duplicates the
plumbing and flags across two commands, and encodes in *two verbs* a distinction consumers
already get from the *format they asked for*. The principle lives in the format's contract
(a versioned JSON schema) and in the docs, not in a fork of the command surface.

### Format as subcommand — `export json`, `export html`

Rejected: each new format would add a subcommand (more surface, more help text) rather than
a value in a list, and shared options (`--output`, the channel selector, `--from-findings`)
would have to be repeated or inherited across every one. `--format` from a registry keeps
the surface flat and the growth trivial.

### Attach to analyze — `analyze-channel --format html`

Rejected outright, and it was the explicit constraint. It chains an offline, format-varied
concern to an expensive network ingest, forcing a re-fetch to re-render, and it hides the
fact that findings are the durable thing and reports are disposable.

### Interactive dashboard under the same verb

A dashboard is not a rendered artifact — it is a served, stateful surface. Cramming "serve
a live dashboard" under `export`/`render` would distort a command whose whole job is
"findings in, one deterministic file out." A dashboard, when it comes, is its own surface
(a `serve`-style command). Naming it out of scope here is deliberate: it keeps `export`
honest rather than making the abstraction bend to a case it does not fit.

## Tradeoffs

- **Gain:** the surface scales by registration, not by CLI edits — the same lever that made
  metrics cheap to add (ADR-006). One flat command, one mental model ("findings → a file in
  the format I asked for"), consistent options across all formats.
- **Gain:** the export/render debate does not fragment the CLI; the exchange/presentation
  line stays where it belongs (the format contract).
- **Give up:** a `--format` value can name a renderer that does not exist until it is
  registered; the error is a runtime "unknown format" listing valid choices, not a compile
  error. Acceptable, and symmetrical with how metrics resolve by name.
- **Give up:** one verb means JSON and PDF share a command even though they serve very
  different consumers. The docs carry the "JSON is the canonical, versioned exchange
  format" note that the verb no longer signals on its own.
- **Defer:** `--from-findings` and any binary-output nuance (a PDF cannot stream to a
  terminal, so it will require `--output`) are named now and built with their PRs, not
  designed in the abstract here.

## Consequences

- The next implementation PR adds `creatoros export <channel> --format {markdown,json}`
  over a small renderer registry (the two existing renderers, registered), with
  `--output` and `--list-formats`. Markdown is the default format. No new dependency.
- The registry is the seam every later format PR plugs into: HTML, PDF, and any exchange
  variant are additive and cross no layer boundary — findings and the `Renderer` protocol
  are untouched.
- **Determinism holds.** Rendering is deterministic given findings + metadata; findings are
  deterministic given the stored rows and an injected `now`. `export` therefore varies only
  with the data and `now`, and the #29 golden files remain the guardrail.
- **Relationship to the knowledge layer (#33).** Once findings are persisted, they become
  the natural input to `export` via `--from-findings`, fully realizing "consume canonical
  findings, render any format" and completing the separation of *deriving* findings from
  *presenting* them.
- **Revisit trigger:** the first output that is not a single deterministic file — an
  interactive dashboard, a live-updating view, or a multi-file bundle. That is a new
  surface (`serve`, or an export that writes a directory), not a new `--format` value, and
  it gets its own ADR.

## Exit strategy

Trivial. No dependency is adopted; `export` is argparse wiring (ADR-004) over the existing
reporting layer. If the single-verb surface ever proves wrong, the command is renamed or
split with a deprecation shim, and the renderer registry — the part with real value —
stays put regardless of the verb in front of it.
