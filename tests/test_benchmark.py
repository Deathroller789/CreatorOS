"""Tests for the pipeline benchmark — it measures, and reports honest structure.

All stages run offline against a synthetic SQLite database built with the real storage
code; ingestion (network) is never exercised here.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from creatoros import analyze, benchmark

NOW = datetime(2026, 7, 12, tzinfo=UTC)

_CHANNEL = {
    "channel_id": "UCbench",
    "handle": "@bench",
    "title": "Bench Channel",
    "description": "d",
    "subscriber_count": 1000,
    "url": "https://youtube.com/@bench",
}


def _video(vid: str, upload_date: str, views: int, title: str) -> dict:
    return {
        "video_id": vid,
        "title": title,
        "upload_date": upload_date,
        "duration": 600,
        "view_count": views,
        "like_count": 10,
        "comment_count": 5,
        "description": "d",
        "url": f"https://youtube.com/watch?v={vid}",
    }


_VIDEOS = [
    _video("a", "20260601", 10_000, "First video"),
    _video("b", "20260611", 50_000, "Second | video"),
    _video("c", "20260621", 2_000, "A much longer third title"),
    _video("d", "20260701", 8_000, "Fourth"),
]


def _seed_db(path: Path) -> None:
    """Populate a database with the synthetic channel using the real storage path."""
    analyze.save(_CHANNEL, _VIDEOS, [], db_path=path)


class RunBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "bench.db"
        _seed_db(self.db)
        self.result = benchmark.run_benchmark(
            channel="UCbench", db_path=self.db, repeats=1, now=NOW
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_measures_all_offline_stages(self) -> None:
        t = self.result.timings
        self.assertIsNone(t.ingestion_s)  # ingestion skipped without --ingest
        self.assertFalse(self.result.ingested)
        for value in (t.metrics_s, t.intelligence_s, t.reporting_s, t.total_s):
            self.assertGreaterEqual(value, 0.0)

    def test_total_excludes_metrics_and_skipped_ingestion(self) -> None:
        # total is the non-overlapping user path; metrics is a component of intelligence
        # and must not be double-counted into it.
        t = self.result.timings
        self.assertEqual(t.total_s, t.intelligence_s + t.reporting_s)

    def test_carries_run_context(self) -> None:
        self.assertEqual(self.result.channel_id, "UCbench")
        self.assertEqual(self.result.sample_size, len(_VIDEOS))
        self.assertEqual(self.result.schema_version, benchmark.BENCHMARK_SCHEMA_VERSION)
        self.assertEqual(self.result.repeats, 1)
        self.assertEqual(self.result.generated_at, "2026-07-12T00:00:00Z")

    def test_json_record_has_stable_shape(self) -> None:
        doc = json.loads(benchmark.to_json(self.result))
        self.assertEqual(
            set(doc),
            {
                "schema_version",
                "generated_at",
                "creatoros_version",
                "git_commit",
                "python_version",
                "platform",
                "channel_id",
                "sample_size",
                "repeats",
                "ingested",
                "timings",
            },
        )
        self.assertEqual(
            set(doc["timings"]),
            {"ingestion_s", "metrics_s", "intelligence_s", "reporting_s", "total_s"},
        )
        self.assertIsNone(doc["timings"]["ingestion_s"])

    def test_human_summary_lists_every_stage(self) -> None:
        text = benchmark.format_human(self.result)
        for stage in ("ingestion", "metrics", "intelligence", "reporting", "total"):
            self.assertIn(stage, text)
        self.assertIn("UCbench", text)

    def test_write_record_writes_a_parseable_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            path = benchmark.write_record(self.result, Path(out))
            self.assertTrue(path.name.startswith("benchmark-"))
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["channel_id"], "UCbench"
            )


class ErrorTests(unittest.TestCase):
    def test_unknown_channel_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "bench.db"
            _seed_db(db)
            with self.assertRaises(benchmark.BenchmarkError):
                benchmark.run_benchmark(channel="nope", db_path=db, repeats=1, now=NOW)

    def test_missing_database_raises(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            self.assertRaises(benchmark.BenchmarkError),
        ):
            benchmark.run_benchmark(
                channel=None, db_path=Path(tmp) / "none.db", repeats=1, now=NOW
            )


if __name__ == "__main__":
    unittest.main()
