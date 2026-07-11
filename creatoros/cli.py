"""CreatorOS command-line interface (MVP).

Run via ``uv run creatoros <command> ...``. Packaging as an installed binary is
deferred until the project matures.

The CLI is an **orchestrator only**: it wires the layers together and reports progress.
It contains no metric formula, no analysis, and no rendering logic — each step is a call
into the layer that owns it (ingestion -> metrics -> intelligence -> reporting). The
intermediate values (raw rows, derived metrics, findings) flow between those calls and
stay inspectable; the CLI invents nothing.

Exit codes: ``0`` success, ``1`` an expected user error (bad URL, empty channel, invalid
option), ``2`` an unexpected internal error. Argparse usage errors follow argparse's
own convention and also exit ``2``.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from datetime import UTC, datetime
from pathlib import Path

from creatoros import analyze
from creatoros.intelligence import build_findings
from creatoros.metrics import compute
from creatoros.reporting import MarkdownRenderer, build_metadata


def _use_utf8(stream: object) -> None:
    """Best-effort switch a stream to UTF-8 so progress glyphs render on capable
    terminals; a no-op where the stream cannot be reconfigured (e.g. under test)."""
    with contextlib.suppress(AttributeError, ValueError):
        stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def _step(message: str) -> None:
    """Print a progress step. Falls back to an ASCII marker if the console encoding
    cannot represent the check glyph, so a legacy code page never crashes the run."""
    try:
        sys.stdout.write(f"✓ {message}\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        sys.stdout.write(f"* {message}\n")
        sys.stdout.flush()


def _write_report(
    rendered: str, channel: dict, output_dir: Path, now: datetime
) -> Path:
    """Persist a rendered report and return its path. LF newline keeps output stable
    across platforms regardless of the local ``core.autocrlf`` setting."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = (channel.get("handle") or channel.get("channel_id") or "channel").lstrip("@")
    path = output_dir / f"{slug}_intelligence_{now:%Y-%m-%d}.md"
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return path


def run_report(
    url: str,
    *,
    limit: int,
    db_path: Path = analyze.DB_PATH,
    output_dir: Path = analyze.OUTPUT_DIR,
    now: datetime | None = None,
) -> Path:
    """Orchestrate the full flow and return the written report path.

    ingest -> metrics -> findings -> render -> save. Each stage is a single call into
    its layer; this function holds no metric, analysis, or rendering logic of its own.
    ``now`` is injectable for deterministic tests.
    """
    now = now or datetime.now(UTC)

    _step("Ingesting...")
    channel, videos, transcripts = analyze.ingest(url, limit=limit, db_path=db_path)
    if not videos:
        raise analyze.AnalyzeError(
            "channel has no videos to analyze; check the URL points at a channel"
        )
    # Transcripts are optional: the V1 report uses metadata only, so absence is a
    # note, not a failure.
    print(
        f"  {len(transcripts)}/{len(videos)} transcripts captured "
        "(report uses video metadata only)."
    )

    _step("Computing metrics...")
    derived = compute(channel, videos, now)

    _step("Running intelligence...")
    findings = build_findings(channel, videos, derived)

    _step("Rendering report...")
    rendered = MarkdownRenderer().render(findings, build_metadata(findings, now=now))

    _step("Saving report...")
    return _write_report(rendered, channel, output_dir, now)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``creatoros`` command."""
    _use_utf8(sys.stdout)
    _use_utf8(sys.stderr)

    parser = argparse.ArgumentParser(prog="creatoros", description="CreatorOS CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_channel = subparsers.add_parser(
        "analyze-channel",
        help="Ingest a YouTube channel and write a channel-intelligence report",
    )
    analyze_channel.add_argument("url", help="YouTube channel URL (any form)")
    analyze_channel.add_argument(
        "--limit",
        type=int,
        default=analyze.DEFAULT_VIDEO_LIMIT,
        metavar="N",
        help=(
            "how many of the channel's latest videos to fetch "
            f"(default: {analyze.DEFAULT_VIDEO_LIMIT})"
        ),
    )

    args = parser.parse_args(argv)

    if args.command == "analyze-channel":
        if args.limit < 1:
            print("error: --limit must be at least 1.", file=sys.stderr)
            return 1
        try:
            path = run_report(args.url, limit=args.limit)
        except analyze.AnalyzeError as exc:
            # Expected, actionable user error (bad URL, network, empty channel).
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:  # noqa: BLE001 — top-level guard: map anything else to 2
            print(f"internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        print(f"\nReport written:\n{path}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
