"""Tests for the CLI orchestrator: the full flow, progress steps, and exit codes.

Network is mocked; the CLI wires real metrics/intelligence/reporting calls over
synthetic data, so these also check the layers compose end to end.
"""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from creatoros import analyze, cli

URL = "https://youtube.com/@demo"
NOW = datetime(2026, 7, 12, tzinfo=UTC)

CHANNEL = {
    "channel_id": "UC123",
    "handle": "@demo",
    "title": "Demo Channel",
    "description": "d",
    "subscriber_count": 1000,
    "url": "https://youtube.com/@demo",
}


def _video(vid: str, upload_date: str, views: int, title: str) -> dict:
    return {
        "video_id": vid,
        "title": title,
        "upload_date": upload_date,
        "duration": 600,
        "view_count": views,
        "like_count": 1,
        "comment_count": 1,
        "description": "d",
        "url": f"https://youtube.com/watch?v={vid}",
    }


VIDEOS = [
    _video("v1", "20260601", 10_000, "First video"),
    _video("v2", "20260615", 50_000, "Second | video"),
    _video("v3", "20260701", 2_000, "A third longer title"),
]


def _mock_ingest(videos: list[dict], transcript: dict | None = None):
    """Patch the two network calls so ingest runs offline against ``videos``."""
    return (
        mock.patch("creatoros.analyze.fetch_channel", return_value=(CHANNEL, videos)),
        mock.patch(
            "creatoros.analyze.fetch_transcript_with_status",
            return_value=(transcript, "ok" if transcript else "unavailable"),
        ),
    )


class RunReportTests(unittest.TestCase):
    def test_writes_intelligence_report(self) -> None:
        fetch_channel, fetch_transcript = _mock_ingest(VIDEOS)
        with (
            tempfile.TemporaryDirectory() as tmp,
            fetch_channel,
            fetch_transcript,
            redirect_stdout(io.StringIO()),
        ):
            db, out = Path(tmp) / "c.db", Path(tmp) / "reports"
            path = cli.run_report(URL, limit=50, db_path=db, output_dir=out, now=NOW)
            self.assertTrue(path.exists())
            self.assertEqual(path.name, "demo_intelligence_2026-07-12.md")
            text = path.read_text(encoding="utf-8")
        self.assertIn("Channel Intelligence", text)
        self.assertIn("Demo Channel", text)
        self.assertIn("descriptive, not predictive", text)  # a real render, not a stub

    def test_prints_the_five_progress_steps_in_order(self) -> None:
        fetch_channel, fetch_transcript = _mock_ingest(VIDEOS)
        buf = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as tmp,
            fetch_channel,
            fetch_transcript,
            redirect_stdout(buf),
        ):
            db, out = Path(tmp) / "c.db", Path(tmp) / "reports"
            cli.run_report(URL, limit=50, db_path=db, output_dir=out, now=NOW)
        output = buf.getvalue()
        steps = [
            "Ingesting",
            "Computing metrics",
            "Running intelligence",
            "Rendering report",
            "Saving report",
        ]
        positions = [output.find(s) for s in steps]
        self.assertNotIn(-1, positions)  # every step printed
        self.assertEqual(positions, sorted(positions))  # and in order

    def test_empty_channel_is_an_actionable_user_error(self) -> None:
        fetch_channel, fetch_transcript = _mock_ingest([])
        with (
            tempfile.TemporaryDirectory() as tmp,
            fetch_channel,
            fetch_transcript,
            redirect_stdout(io.StringIO()),
            self.assertRaises(analyze.AnalyzeError) as ctx,
        ):
            db = Path(tmp) / "c.db"
            cli.run_report(URL, limit=50, db_path=db, output_dir=Path(tmp), now=NOW)
        self.assertIn("no videos", str(ctx.exception))

    def test_discloses_when_fewer_videos_are_received_than_requested(self) -> None:
        # #41: 3 videos returned for a --limit of 50 must be surfaced, not hidden.
        fetch_channel, fetch_transcript = _mock_ingest(VIDEOS)
        buf = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as tmp,
            fetch_channel,
            fetch_transcript,
            redirect_stdout(buf),
        ):
            db, out = Path(tmp) / "c.db", Path(tmp) / "reports"
            cli.run_report(URL, limit=50, db_path=db, output_dir=out, now=NOW)
        output = buf.getvalue()
        self.assertIn("requested 50", output)
        self.assertIn("received 3", output)

    def test_no_under_delivery_note_when_the_sample_is_full(self) -> None:
        fetch_channel, fetch_transcript = _mock_ingest(VIDEOS)
        buf = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as tmp,
            fetch_channel,
            fetch_transcript,
            redirect_stdout(buf),
        ):
            db, out = Path(tmp) / "c.db", Path(tmp) / "reports"
            cli.run_report(URL, limit=len(VIDEOS), db_path=db, output_dir=out, now=NOW)
        self.assertNotIn("requested", buf.getvalue())

    def test_missing_transcripts_do_not_fail_the_run(self) -> None:
        fetch_channel, fetch_transcript = _mock_ingest(VIDEOS, transcript=None)
        with (
            tempfile.TemporaryDirectory() as tmp,
            fetch_channel,
            fetch_transcript,
            redirect_stdout(io.StringIO()),
        ):
            db, out = Path(tmp) / "c.db", Path(tmp) / "reports"
            path = cli.run_report(URL, limit=50, db_path=db, output_dir=out, now=NOW)
            self.assertTrue(path.exists())


class ExitCodeTests(unittest.TestCase):
    def test_success_returns_zero(self) -> None:
        with (
            mock.patch("creatoros.cli.run_report", return_value=Path("x")),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(cli.main(["analyze-channel", URL]), 0)

    def test_expected_user_error_returns_one(self) -> None:
        err = io.StringIO()
        with (
            mock.patch(
                "creatoros.cli.run_report", side_effect=analyze.AnalyzeError("bad url")
            ),
            redirect_stderr(err),
        ):
            code = cli.main(["analyze-channel", URL])
        self.assertEqual(code, 1)
        self.assertIn("bad url", err.getvalue())

    def test_unexpected_error_returns_two(self) -> None:
        err = io.StringIO()
        with (
            mock.patch("creatoros.cli.run_report", side_effect=RuntimeError("kaboom")),
            redirect_stderr(err),
        ):
            code = cli.main(["analyze-channel", URL])
        self.assertEqual(code, 2)
        self.assertIn("internal error", err.getvalue())

    def test_limit_below_one_returns_one(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli.main(["analyze-channel", URL, "--limit", "0"])
        self.assertEqual(code, 1)
        self.assertIn("--limit", err.getvalue())

    def test_passes_limit_through(self) -> None:
        with (
            mock.patch("creatoros.cli.run_report", return_value=Path("x")) as rr,
            redirect_stdout(io.StringIO()),
        ):
            cli.main(["analyze-channel", URL, "--limit", "3"])
        self.assertEqual(rr.call_args.kwargs["limit"], 3)

    def test_defaults_to_default_limit(self) -> None:
        with (
            mock.patch("creatoros.cli.run_report", return_value=Path("x")) as rr,
            redirect_stdout(io.StringIO()),
        ):
            cli.main(["analyze-channel", URL])
        self.assertEqual(rr.call_args.kwargs["limit"], analyze.DEFAULT_VIDEO_LIMIT)


if __name__ == "__main__":
    unittest.main()
