"""Pipeline benchmark — measure, never optimize.

Times each layer of the CreatorOS pipeline and the end-to-end total, then emits both a
human-readable summary and a machine-readable JSON record so timings can be tracked over
time. This is a measurement tool only: it changes no behavior and makes no performance
decision — it reports where time goes and stops there.

Stages measured (public entry points):

- **ingestion** — fetch + store. Network-bound and it mutates the database, so it runs
  only when an explicit ``--ingest URL`` is given; otherwise it is reported as skipped.
- **metrics** — the derived-metrics engine (:func:`creatoros.metrics.compute`) in
  isolation. This is a *component* of intelligence, not an extra stage.
- **intelligence** — the full :func:`analyze_channel` stage (it loads rows, runs the
  metrics engine, and assembles findings).
- **reporting** — both renderers over the produced findings.

``total`` is the non-overlapping user path: ``ingestion + intelligence + reporting``.
Metrics is measured separately to show where intelligence spends its time; it is a
subset of intelligence and is deliberately *not* added into the total.

Run it with::

    uv run python -m creatoros.benchmark            # offline stages, existing DB
    uv run python -m creatoros.benchmark --ingest <url>   # also time a real fetch
"""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import statistics
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from creatoros import analyze
from creatoros.intelligence import analyze_channel
from creatoros.intelligence.analyze import DB_PATH
from creatoros.metrics import compute
from creatoros.reporting import JsonRenderer, MarkdownRenderer, build_metadata

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = REPO_ROOT / "output" / "benchmarks"

# Bump when the JSON record's structure changes, so a stored history can be read against
# the right expectations.
BENCHMARK_SCHEMA_VERSION = 1

# Offline stages are sub-millisecond and noisy; time each a few times and take the
# median so a single scheduler hiccup does not dominate the number.
DEFAULT_REPEATS = 5


class BenchmarkError(Exception):
    """Raised when the benchmark cannot run (no database, channel not found, etc.)."""


@dataclass(frozen=True)
class StageTimings:
    """Per-stage wall-clock seconds. ``ingestion_s`` is ``None`` when ingestion is
    skipped; ``metrics_s`` is a component of ``intelligence_s``, not part of the
    total."""

    ingestion_s: float | None
    metrics_s: float
    intelligence_s: float
    reporting_s: float
    total_s: float


@dataclass(frozen=True)
class BenchmarkResult:
    """One benchmark run: its timings plus the context needed to compare runs."""

    schema_version: int
    generated_at: str
    creatoros_version: str
    git_commit: str | None
    python_version: str
    platform: str
    channel_id: str
    sample_size: int
    repeats: int
    ingested: bool
    timings: StageTimings


def _measure(fn: Callable[[], Any]) -> float:
    """Wall-clock seconds for a single call."""
    start = perf_counter()
    fn()
    return perf_counter() - start


def _median_seconds(fn: Callable[[], Any], repeats: int) -> float:
    """Median wall-clock seconds over ``repeats`` calls (repeats >= 1)."""
    return statistics.median(_measure(fn) for _ in range(max(1, repeats)))


def _git_commit() -> str | None:
    """Short HEAD commit, or ``None`` if git is unavailable / this is not a checkout."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout.strip() or None


def _first_channel(db_path: Path) -> str:
    """The first stored channel_id — the default target for the offline stages."""
    if not db_path.exists():
        raise BenchmarkError(f"no database at {db_path}; ingest a channel first")
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT channel_id FROM channels ORDER BY channel_id LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise BenchmarkError("no channels in the database; ingest one first")
    return row[0]


def _load_rows(channel: str, db_path: Path) -> tuple[dict, list[dict]]:
    """Read the raw channel + video rows. The benchmark's own raw read, used only to
    feed the metrics engine in isolation (it mirrors the intelligence layer's load)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        crow = conn.execute(
            "SELECT * FROM channels WHERE channel_id = ? OR handle = ? LIMIT 1",
            (channel, channel),
        ).fetchone()
        if crow is None:
            raise BenchmarkError(f"channel {channel!r} not found; ingest it first")
        raw_channel = dict(crow)
        videos = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM videos WHERE channel_id = ?",
                (raw_channel["channel_id"],),
            )
        ]
    finally:
        conn.close()
    if not videos:
        raise BenchmarkError(f"channel {channel!r} has no stored videos")
    return raw_channel, videos


def _ingest(url: str, limit: int, db_path: Path) -> str:
    """Fetch + store a channel; return its channel_id. The timed ingestion stage."""
    channel, videos = analyze.fetch_channel(url, limit=limit)
    transcripts: list[dict] = []
    for v in videos:
        transcript = analyze.fetch_transcript(v["video_id"])
        if transcript:
            transcripts.append(transcript)
    analyze.save(channel, videos, transcripts, db_path=db_path)
    return channel["channel_id"]


def run_benchmark(
    channel: str | None = None,
    db_path: Path = DB_PATH,
    ingest_url: str | None = None,
    limit: int = analyze.DEFAULT_VIDEO_LIMIT,
    repeats: int = DEFAULT_REPEATS,
    now: datetime | None = None,
) -> BenchmarkResult:
    """Measure the pipeline and return a :class:`BenchmarkResult`. No file I/O.

    With ``ingest_url`` set, a real fetch is timed once (network) and its channel
    becomes the target for the offline stages. Otherwise ingestion is skipped and
    ``channel`` (or the first stored channel) is used. ``now`` is injectable for tests.
    """
    now = now or datetime.now(UTC)

    ingestion_s: float | None = None
    if ingest_url is not None:
        ingested_id: list[str] = []
        ingestion_s = _measure(
            lambda: ingested_id.append(_ingest(ingest_url, limit, db_path))
        )
        channel = channel or ingested_id[0]

    channel = channel or _first_channel(db_path)
    raw_channel, videos = _load_rows(channel, db_path)

    metrics_s = _median_seconds(lambda: compute(raw_channel, videos, now), repeats)
    intelligence_s = _median_seconds(
        lambda: analyze_channel(channel, db_path, now), repeats
    )

    findings = analyze_channel(channel, db_path, now)
    metadata = build_metadata(findings, now=now)
    markdown, as_json = MarkdownRenderer(), JsonRenderer()
    reporting_s = _median_seconds(
        lambda: (
            markdown.render(findings, metadata),
            as_json.render(findings, metadata),
        ),
        repeats,
    )

    total_s = (ingestion_s or 0.0) + intelligence_s + reporting_s
    return BenchmarkResult(
        schema_version=BENCHMARK_SCHEMA_VERSION,
        generated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        creatoros_version=metadata.creatoros_version,
        git_commit=_git_commit(),
        python_version=platform.python_version(),
        platform=platform.platform(),
        channel_id=findings.channel.channel_id,
        sample_size=findings.sample_size,
        repeats=max(1, repeats),
        ingested=ingestion_s is not None,
        timings=StageTimings(
            ingestion_s=ingestion_s,
            metrics_s=metrics_s,
            intelligence_s=intelligence_s,
            reporting_s=reporting_s,
            total_s=total_s,
        ),
    )


def to_json(result: BenchmarkResult) -> str:
    """The machine-readable record: a stable-shape JSON document, trailing newline."""
    return json.dumps(asdict(result), indent=2) + "\n"


def write_record(result: BenchmarkResult, benchmark_dir: Path = BENCHMARK_DIR) -> Path:
    """Append one JSON record to the benchmark history directory; return its path."""
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    path = benchmark_dir / f"benchmark-{result.generated_at.replace(':', '')}.json"
    path.write_text(to_json(result), encoding="utf-8", newline="\n")
    return path


def _fmt(seconds: float | None) -> str:
    if seconds is None:
        return "skipped"
    return f"{seconds * 1000:.2f} ms" if seconds < 1 else f"{seconds:.3f} s"


def format_human(result: BenchmarkResult) -> str:
    """A readable summary of one run."""
    t = result.timings
    return "\n".join(
        [
            "CreatorOS pipeline benchmark",
            f"  channel:    {result.channel_id} (n={result.sample_size})",
            f"  commit:     {result.git_commit or 'unknown'}",
            f"  generated:  {result.generated_at}",
            f"  python:     {result.python_version} · {result.platform}",
            f"  repeats:    {result.repeats} (offline stages, median)",
            "",
            f"  ingestion       {_fmt(t.ingestion_s)}",
            f"  metrics         {_fmt(t.metrics_s)}",
            f"  intelligence    {_fmt(t.intelligence_s)}",
            f"  reporting       {_fmt(t.reporting_s)}",
            "  ------------------------",
            f"  total           {_fmt(t.total_s)}",
            "",
            "  metrics is a component of intelligence; "
            "total = ingestion + intelligence + reporting.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: measure the pipeline, print a summary, and write a JSON record."""
    parser = argparse.ArgumentParser(
        prog="creatoros-benchmark",
        description="Measure CreatorOS pipeline stage timings (measurement only).",
    )
    parser.add_argument(
        "--channel", help="stored channel_id or handle (default: first in the DB)"
    )
    parser.add_argument("--db", type=Path, default=DB_PATH, help="database path")
    parser.add_argument(
        "--ingest",
        metavar="URL",
        help="also time a real ingestion of this channel URL (network; mutates the DB)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=analyze.DEFAULT_VIDEO_LIMIT,
        metavar="N",
        help="videos to fetch when --ingest is used",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=DEFAULT_REPEATS,
        metavar="N",
        help=f"runs per offline stage; median reported (default {DEFAULT_REPEATS})",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the JSON record to stdout"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BENCHMARK_DIR,
        help="where to write the record",
    )
    args = parser.parse_args(argv)

    try:
        result = run_benchmark(
            channel=args.channel,
            db_path=args.db,
            ingest_url=args.ingest,
            limit=args.limit,
            repeats=args.repeats,
        )
    except BenchmarkError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    path = write_record(result, args.output_dir)
    print(to_json(result), end="") if args.json else print(format_human(result))
    print(f"JSON record: {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
