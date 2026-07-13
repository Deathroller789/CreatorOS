# Channel analysis checklist

Run this checklist **every time** CreatorOS analyzes a channel during
[Phase 2 — real-world usage](../PROJECT_PHASES.md).
Its only purpose is to capture honest product feedback while the tool is fresh in mind, and to
convert friction into GitHub issues.

This is not a quality gate on the *channel* — it is a feedback gate on **CreatorOS**.
Answer fast and honestly; a lukewarm "sort of" is more useful than a polite "yes".

## Per-analysis checklist

Copy this block into notes (or an issue) for each channel analyzed.

```text
Channel:            <name / URL>
Niche:              <horror / finance / tech / education / other>
Date analyzed:      <YYYY-MM-DD>

□ Did the analysis feel useful?
□ Was anything confusing?
□ What information did I wish existed?
□ What required manual work?
□ Were the findings actually actionable?
□ Did confidence feel honest?
□ Was anything obviously missing?
□ Did I discover a repeated frustration?
□ Should this become a GitHub issue?
□ If yes: bug / enhancement / research?

Notes:
```

## How to use the answers

- **Anything confusing, missing, or manual** is a candidate issue. File it — small frictions are
  easy to forget and are exactly the signal Phase 2 exists to collect.
- **"Did confidence feel honest?"** is load-bearing. CreatorOS is descriptive and
  confidence-bounded on purpose; if a finding felt over- or under-confident, that is a real
  defect in the intelligence, not a nitpick.
- **Watch for repetition.** A frustration felt on one channel is noise; the *same* frustration
  across many channels is signal, and signal is what becomes future product work.
- **Label every issue** bug / enhancement / research, so the pattern across issues is legible
  later.

## What not to do

- Do **not** fix things ad hoc mid-phase or start building features — Phase 2's output is issues
  and observations, not code (see [PROJECT_PHASES.md](../PROJECT_PHASES.md)).
- Do **not** invent improvements the usage did not actually surface.
- Do **not** skip the checklist because an analysis "seemed fine" — the quiet, friction-free runs
  are themselves a useful data point.
