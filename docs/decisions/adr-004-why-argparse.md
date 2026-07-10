# ADR-004: Why `argparse` (no CLI framework)?

- **Status:** Accepted
- **Date:** 2026-07-10 (recorded retroactively; decision made during Sprint 2)

## Context

CreatorOS is used through a CLI (`uv run creatoros <command>`). Sprint 2 introduced the
first command, `analyze-channel`, and needed argument parsing and subcommands. Confirmed by
the [reuse audit](../../research/technology/reuse_audit.md).

## Decision

Use the standard library **`argparse`** with subparsers. Do not add a CLI framework.

## Alternatives

- **Typer** — modern, type-hint driven, excellent ergonomics; but it pulls in Click and its
  dependencies for convenience we don't yet need.
- **Click** — mature decorator API, nested commands, validation; still a dependency.
- **docopt** — effectively unmaintained.

## Tradeoffs

- **Gain:** zero dependencies; always available; sufficient for a handful of subcommands.
- **Give up:** ergonomics. `argparse` gets verbose as a CLI grows, and lacks Typer's
  type-driven validation and nicer help output.

## Consequences

- The CLI stays dependency-free while the command surface is small.
- **Revisit trigger:** once CreatorOS has roughly six or more commands (the long-term vision
  lists many: `analyze-patterns`, `compare-channels`, `detect-patterns`, …) or needs rich
  validation, re-evaluate Typer. Adopting it would then remove more code than it adds.

## Exit strategy

**None needed.** Standard library; migrating to Typer/Click later is a mechanical,
localized change confined to `creatoros/cli.py`.
