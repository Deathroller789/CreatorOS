# ADR-009: Error philosophy — categories, exit codes, and user experience

- **Status:** Accepted
- **Date:** 2026-07-13

## Context

The CLI orchestration work ([#31](https://github.com/Deathroller789/CreatorOS/pull/31))
established the first pieces of an error policy: exit codes `0`/`1`/`2`, actionable messages
over generic ones, and one concrete judgement call — a missing transcript is a *note*, not a
failure, because the V1 report uses metadata only. That was decided in one command. As more
commands arrive (`export`, `benchmark`, and whatever follows), they need to fail the *same*
way, so a user learns the system's behavior once.

CreatorOS also spans two very different failure worlds. **Ingestion** is network-bound:
timeouts, rate limits, and a single unavailable video are normal and expected. **Metrics,
intelligence, and reporting** are deterministic and offline: a failure there is a bug or bad
input, not weather. A single error philosophy has to serve both without pretending they are
the same.

The five terms to define — recoverable, unrecoverable, retry, warning, partial success — are
not one flat list. They are three different things, and conflating them is the usual source
of bad error handling. This ADR separates them and maps them onto the `0`/`1`/`2` contract.

## Decision

Model failure along three axes, and define the five terms against them:

- A **condition** is either **transient** (might succeed if tried again — a timeout, a `429`)
  or **permanent** (will fail identically on retry — a bad URL, a `404`). Independently, it is
  either **unit-scoped** (dooms one item — one video) or **run-fatal** (dooms the whole run).
- A **response** is what we do: continue, warn, **retry**, skip, or abort.
- An **outcome** is how the run ends: full success, **partial success**, or failure — and
  that is what the exit code reports.

### The five terms

- **Warning** — a condition worth telling the user about that does **not** compromise the
  validity of the result. The run continues and its output is correct for its purpose.
  _Example:_ "2 of 5 videos had no transcript; the report uses video metadata only." A
  warning never changes the exit code — the run still succeeds.
- **Recoverable** — a failure the system can work around by dropping the affected unit and
  continuing, **or** one the user can fix and re-run. The first flavour (skip one video, keep
  the rest) produces a partial success; the second (bad URL, empty channel, invalid option)
  aborts the run but with an actionable message, because the user holds the fix.
- **Unrecoverable** — a failure that leaves no usable result; the run aborts. Two causes,
  two exit codes: **expected and user-caused** (bad input, nothing to analyze) exits `1` with
  an actionable message; **unexpected and internal** (a bug, an impossible state) exits `2`
  with an honest internal-error report.
- **Retry** — not a severity but a **response** to a *transient* condition: try the operation
  again, with backoff, before concluding it failed. Retry turns a transient blip into either
  eventual success or — once attempts are exhausted — a recoverable skip (if unit-scoped) or
  an unrecoverable abort (if run-fatal). Only idempotent, transient, network operations are
  retried; a permanent error is never retried.
- **Partial success** — the **outcome** when one or more recoverable failures occurred but a
  usable result was still produced. It is a *success* (exit `0`), always reported with a
  visible summary of what was degraded or skipped. Silent partial success is forbidden — the
  user must never mistake an incomplete result for a complete one.

### Condition → response → outcome → exit code

| Condition | Response | Outcome | Exit |
|-----------|----------|---------|------|
| Notable but non-compromising | warn, continue | success (with a note) | `0` |
| Transient, unit-scoped (video fetch times out) | retry; then skip if still failing | partial success | `0` |
| Permanent, unit-scoped (one video unavailable) | skip, warn | partial success | `0` |
| Transient, run-fatal (channel fetch times out) | retry; then abort if still failing | failure (expected) | `1` |
| Permanent, run-fatal, user-fixable (bad URL, empty channel) | abort with a fix | failure (expected) | `1` |
| Unexpected / internal (bug, impossible state) | abort, report honestly | failure (internal) | `2` |

### Error provenance — every error has an owner

Independently of severity, every error names its **source** — who or what caused it — whenever
that source is identifiable. Four owners:

| Owner | Meaning | Example |
|-------|---------|---------|
| **User** | The input or invocation is at fault | bad URL, empty channel, invalid option |
| **Environment** | The machine or runtime around us | no disk space, missing runtime, a cp1252 console |
| **Dependency** | An external tool or service we rely on | yt-dlp scrape breaks, YouTube `429`, transcript API down |
| **CreatorOS** | Our own code | a bug, an impossible state, a broken invariant |

Provenance is orthogonal to the condition/response/outcome axes: a `429` is transient, run-fatal,
*and* owned by a Dependency.
It sharpens the message — a User error says what to fix, a Dependency error says what failed and
that it is not the user's fault, an Environment error names the missing capability, and a CreatorOS
error owns the bug — and it protects blame-assignment: a dependency breaking is never reported as
user error, and our own bug is never blamed on the user.
Provenance also anchors the `1`-vs-`2` split: User, Environment, and Dependency failures are
*expected* (exit `1` when run-fatal, `0` when skippable); only a CreatorOS-owned failure is
*internal* and exits `2`.
When the source cannot be determined, say so rather than guessing — attributing an error to the
wrong owner is itself a failure.

### Unavailable versus missing — preserve uncertainty

CreatorOS distinguishes **missing** (we looked, and it is genuinely not there) from **unavailable**
(we could not obtain it right now) and **unknown** (we never established it either way).
These are not synonyms, and collapsing them into "missing" invents a certainty the system does not
have.

_Example:_ a video with no transcript may be one that genuinely **has** no transcript (missing), one
whose transcript we were rate-limited out of fetching (unavailable), or one we never attempted
(unknown). Reporting all three as "no transcript" lets a transient fetch failure masquerade as a
settled fact about the channel.

The rule: **never assert an absence you have not verified.** A metric with no input is
`None`/"unknown" (ADR-006's null propagation already carries this through the metric graph), a fetch
that failed is "unavailable", and only a confirmed lookup returns "missing".
This is the error-handling face of the intelligence discipline (ADR-006): descriptive not
predictive, preserve uncertainty, and "unknown" is an acceptable answer.

## User-experience philosophy, per category

The exit code is for scripts; the *message* is for a person. Each category has a distinct
voice.

- **Warning — calm and informative.** State what happened, its impact, and that the run is
  continuing ("…using video metadata only"). Group and summarize rather than spam one line per
  occurrence. Never alarming, never a stack trace.
- **Recoverable (skip) — matter-of-fact.** Name what was dropped and why, in one line, and
  fold it into the partial-success summary. The user should be able to decide whether the gap
  matters.
- **Retry — nearly invisible.** The user cares about the outcome, not the attempts. At most a
  single unobtrusive "retrying…" note; never a wall of tracebacks for transient blips. Surface
  only the final result of the retry loop.
- **Unrecoverable, user-caused — one actionable sentence.** Say what is wrong and what to do
  ("channel has no videos to analyze; check the URL points at a channel"). No stack trace — it
  is not a bug, and a trace only obscures the fix. Exit `1`.
- **Unrecoverable, internal — honest and diagnostic.** Admit it is a bug, name the error type
  and message, and point to where to report it. A traceback is acceptable here, because the
  audience is whoever debugs it. Exit `2`. Never dress an internal failure up as user error, or
  vice versa.
- **Partial success — deliver, then disclose.** Give the result first, then a prominent summary
  of what was degraded ("Report written. 2/5 transcripts missing; 1 video skipped."). Exit `0`,
  but the degradation is impossible to miss.

Cutting across all of them: **actionable over generic** (from #31), **never hide degradation**,
**fail helpful for the user and loud for ourselves**, and **one behavior across every command**.

## Alternatives

- **Two categories — error or ok.** The default most CLIs drift into. Rejected: it cannot
  express "continue without transcripts", so either a normal metadata-only run fails, or a real
  degradation passes silently. The whole point is the middle ground.
- **A distinct exit code for partial success** (e.g. `3`). Tempting for scripts that want to
  branch on "complete vs incomplete". Rejected: it breaks the `0`/`1`/`2` contract from #31 and
  the Unix convention that `0` means "it ran and produced output". Partial success *is* success;
  the degradation belongs in the output, where a human sees it, not in a code most scripts
  ignore. Revisit only if a real automation consumer needs to branch on it.
- **Retry everything, or retry nothing.** Rejected both ways. Retrying permanent errors wastes
  time and hammers a service that already said no; retrying nothing makes ingestion fragile
  against normal network weather. Retry exactly the transient, idempotent network operations.
- **Treat warnings as errors** ("strict mode"). Rejected as the default: it would fail the
  common, healthy metadata-only run. A future opt-in `--strict` could promote warnings to
  failures for automation that demands completeness — named, not built.

## Tradeoffs

- **Gain:** predictable behavior — a user (and a script) learns the system's failure model once
  and it holds everywhere. Degradation is always visible; internal bugs are never disguised as
  user error.
- **Gain:** ingestion can be resilient (retry, skip) without ever silently shipping a hollow
  result.
- **Give up:** discipline at every call site — each command must classify its failures into
  this model rather than letting an exception escape. The top-level `2` guard from #31 is the
  safety net that catches whatever slips through.
- **Give up:** the ability to branch a script on partial-vs-full success by exit code alone.
  Accepted deliberately; the summary in the output carries that signal instead.

## Consequences

- The transcript-note behavior from #31 is now the reference implementation of a *warning +
  partial success*, not a one-off — future commands follow the same pattern.
- The near-term concrete work this licenses (in its own PR, not here): **retry with backoff on
  transient ingestion failures** (`429`/`5xx`/timeouts), and a **partial-success summary** when
  videos are skipped. Neither changes a layer boundary.
- Exit codes stay `0`/`1`/`2` exactly as #31 defined them; this ADR only says which conditions
  land on which code, and why. Argparse usage errors keep their own `2` (ADR-004 / #31).
- **Revisit trigger:** the first automation consumer that must distinguish partial from full
  success programmatically (reopens the "exit code `3` vs `--strict`" question), or the first
  failure mode that does not fit these three axes.
- Every error now carries an **owner** (User / Environment / Dependency / CreatorOS) and every
  absence is stated as **missing**, **unavailable**, or **unknown** — not flattened into one. Both
  are part of the contract each command implements, alongside the exit-code mapping.

## Exit strategy

Trivial — this is policy, not code or dependency. If the taxonomy proves wrong, it is reworded
in one document and the call sites follow. The `0`/`1`/`2` contract it sits on is the stable
part and is unaffected either way.
