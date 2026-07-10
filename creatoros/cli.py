"""CreatorOS command-line interface (MVP).

Run via ``uv run creatoros <command> ...``. Packaging as an installed binary is
deferred until the project matures.
"""

from __future__ import annotations

import argparse

from creatoros import analyze


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``creatoros`` command."""
    parser = argparse.ArgumentParser(prog="creatoros", description="CreatorOS CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_channel = subparsers.add_parser(
        "analyze-channel",
        help="Fetch a YouTube channel + latest videos and write a report",
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
            parser.error("--limit must be at least 1")
        try:
            analyze.run(args.url, limit=args.limit)
        except analyze.AnalyzeError as exc:
            print(f"error: {exc}")
            return 1
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
