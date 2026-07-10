# Research Standard

Rules for every research report produced for CreatorOS. A report that does not follow
this structure is not done. This exists so a decision made today can be trusted, or
overturned with evidence, a year from now.

## Required sections

Every research report **must** contain these sections, in this order:

1. **Summary** — the answer in 3–5 sentences. State the recommendation up front. A reader
   who stops here should still know what to do.
2. **Evidence** — the findings that support the summary. Facts, benchmarks, tests,
   quotes, comparison tables. No unsupported claims.
3. **Confidence** — `High` / `Medium` / `Low`, plus one sentence on why. What would have
   to be true for this to be wrong?
4. **Sources** — every source used, as links, with the date accessed. Primary sources
   (docs, source code, changelogs) over secondary (blogs, forums). No citation, no claim.
5. **Open Questions** — what we still don't know, and what we deliberately did not check.
6. **Next Actions** — concrete follow-ups, each a single verb-first line.

## Reuse audit

Before building or expanding any capability, and before adopting a dependency, first audit
what already exists (ENGINEERING.md principle 1). A reuse audit is short:

1. **Existing solutions** — open-source projects, MCP servers, and libraries that already
   solve most of the problem.
2. **Maintenance status** — active? recent releases? healthy community?
3. **Pros / cons** — per option.
4. **Adopt / wrap / build** — the recommendation. **Default to wrapping** existing
   infrastructure unless building ourselves gives CreatorOS a clear competitive advantage.

The reuse audit precedes — and may fold into — the dependency evaluation below.

## Dependency & technology evaluations

Evaluating a dependency, library, or tool before installing it (required by
[ENGINEERING.md](../ENGINEERING.md) principle 2) uses this specific structure instead of
the six sections above:

1. **Problem** — what we need solved, and the constraints.
2. **Options** — the candidates considered (including "build it ourselves" and "reuse an
   existing project / MCP server").
3. **Comparison** — a table across the options on the axes that matter (maintenance,
   accuracy, speed, long-term reliability — not popularity), with sources.
4. **Winner** — the single recommended choice.
5. **Tradeoffs** — what the winner gives up.
6. **Future Risks** — what could make this the wrong call later.
7. **Exit Strategy** — *if this project dies tomorrow, how hard is it to replace?* State a
   replacement difficulty (None / Low / Medium / High) and the escape path. A dependency we
   cannot leave is a liability, no matter how good. Reject or wrap anything that can't rate
   at least Low.
8. **Confidence** — High / Medium / Low, with why.
9. **Recommendation** — the actionable decision. If adopted, it also gets an ADR.

"No evaluation, no install." These evaluations live in `research/technology/`.

## Rules

- **Reuse first.** Always check for an existing project/MCP/library that solves ≥90% of
  the problem before proposing custom code (ENGINEERING.md principle 1).
- **Recommend, don't survey.** A comparison must end in one named winner and the reason.
  "It depends" is only acceptable with the specific conditions spelled out.
- **Ignore popularity.** Stars, downloads, and hype are not evidence. Maintenance,
  correctness, speed, and long-term reliability are.
- **Cite or cut.** Any factual claim without a source in the Sources section is removed.
- **Date everything.** Libraries and services change; a report is a snapshot. Put the
  report date in the Summary.
- **State confidence honestly.** Low confidence with a clear open question beats false
  certainty.
- **One topic per report.** If it spans multiple decisions, split it.

Reports live in `research/`, sorted into its category subfolders (`technology/`,
`market/`, `competitors/`, `experiments/`, `reports/`). Technology, library, and stack
evaluations go in `research/technology/`. A report that leads to a binding choice also
gets an ADR in `docs/decisions/`.
