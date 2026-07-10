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

    args = parser.parse_args(argv)

    if args.command == "analyze-channel":
        try:
            analyze.run(args.url)
        except analyze.AnalyzeError as exc:
            print(f"error: {exc}")
            return 1
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
