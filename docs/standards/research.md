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

## Rules

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

Reports live in `research/`. Technology/stack evaluations live in
`research/stack_evaluation/`. A report that leads to a binding choice also gets a record
in `docs/decisions/`.
