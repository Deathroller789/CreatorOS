# Project Vision

_First draft, written by the assistant from the current state of CreatorOS. This document
is owned by the human and is meant to be revised. It defines direction and how we decide —
not how anything is built._

## Mission

CreatorOS is a private, durable operating system for a creator's work. Its job is to turn
scattered creative output and data into compounding, trustworthy knowledge and
automation that the creator owns and controls. It exists to give one person the leverage
of a well-run system — one that is still understandable, correct, and useful years from
now.

## Philosophy

- **Built to last.** Every choice is judged against a simple test: will this still make
  sense a year from now? We optimize for a maintainable system, not for finishing tasks
  quickly.
- **One source of truth.** State lives in a single, authoritative, inspectable place.
  Nothing important is hidden or duplicated. If two things disagree, that's a bug.
- **Explicit over implicit.** The system does not remember, change, or act on its own in
  ways the creator can't see. No magic. No silent state.
- **Deliberate over reflexive.** We do not add tools, libraries, or services on impulse.
  Everything earns its place with a written evaluation first.
- **Knowledge compounds.** We research a question once, write it down, and never ask
  twice. Decisions and their reasoning are recorded so the past is legible.
- **The human is in control.** The assistant proposes, researches, and executes within
  the rules; the human owns the vision and the hard, irreversible calls.

## Design principles

1. **Single, auditable source of truth.** All durable state is stored where any tool can
   read it and a person can inspect it.
2. **Transparency by default.** Behavior, data, and decisions are visible and reviewable.
   Prefer boring, well-understood mechanisms over clever ones.
3. **Fewest moving parts.** Simplicity is a feature. Reach for the simplest thing that
   works; add complexity only when a real need proves it necessary.
4. **Composable capabilities.** The system is built from small tools that each do one job
   well and can be combined, not one large tangled program.
5. **Standards are enforced, not suggested.** Shared rules for code, docs, naming,
   structure, and research keep the system coherent as it grows.
6. **Own the data.** Local-first. The creator's information stays under the creator's
   control; external services are a deliberate choice, never a default.
7. **Reversible by preference.** Favor decisions that are easy to undo. When a choice is
   hard to reverse, slow down and write it down.

## Long-term goals

- A knowledge base that **compounds** over time — every piece of research and every
  decision makes the next one faster and better-informed.
- A growing set of **reliable, reusable capabilities** for the platforms the creator
  works on, built on shared infrastructure rather than one-off scripts.
- **Automation the creator directs** — leverage that amplifies the person, on their
  terms, without taking control away from them.
- A system that a newcomer (or a future version of the creator) can **understand in an
  afternoon** by reading its documents.

## Non-goals

- **Not a demo or a hackathon project.** Speed of shipping is not the measure of success;
  durability and correctness are.
- **Not feature-maximizing.** We do not add capabilities for their own sake. Fewer,
  trustworthy features beat many fragile ones.
- **Not trend-chasing.** Popularity, hype, and novelty are not reasons to adopt anything.
- **Not opaque automation.** The system will not accumulate hidden memory or act behind
  the creator's back.
- **Not a product for others (for now).** CreatorOS is the creator's own operating
  system, not a general-purpose SaaS. That can change only by explicit decision.

## Constraints

- **Local-first.** The default home for data and execution is the creator's own machine.
- **Small-team maintainable.** The system must remain operable and understandable by one
  person working with an assistant.
- **Human-owned boundaries.** Certain documents and irreversible decisions belong to the
  human; the assistant does not overwrite them or decide them alone.
- **Standards apply to everything.** New work conforms to the established rules or the
  rules are deliberately changed first.
- **The one-year test is binding.** Any decision that wouldn't hold up a year out is not
  ready.

## How decisions are made

1. **Research first.** A question worth deciding gets a written report — evidence,
   confidence, sources, open questions, next actions — ending in a clear recommendation.
2. **Evaluate before adopting.** No new dependency, library, service, or tool enters the
   system without a written evaluation of the alternatives and their tradeoffs.
3. **Record the decision.** Binding choices become numbered decision records that explain
   the context, the options, the choice, and the condition under which we'd revisit it.
4. **Never ask twice.** Once something is researched or decided, it is written down and
   reused, not re-litigated.
5. **The human decides the hard forks.** For choices that are costly or hard to reverse,
   the assistant lays out options and a recommendation; the human chooses.
6. **When in doubt, defer.** Prefer the reversible, simpler path, or wait until the need
   is concrete enough to decide well.
