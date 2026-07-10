"""High-value tests for the analyze-channel vertical slice (issue #1).

Stdlib ``unittest`` only — no test-framework dependency (ENGINEERING.md principle 3).
All network access (yt-dlp, youtube-transcript-api) is mocked.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from creatoros import analyze
from creatoros.cli import main
from yt_dlp.utils import DownloadError

URL = "https://youtube.com/@demo"

CHANNEL = {
    "channel_id": "UC123",
    "handle": "@demo",
    "title": "Demo Channel",
    "description": "desc",
    "subscriber_count": 1000,
    "url": "https://www.youtube.com/channel/UC123",
}
VIDEOS = [
    {
        "video_id": "vid1",
        "title": "First | video",
        "upload_date": "20260101",
        "duration": 3661,
        "view_count": 1234,
        "like_count": 10,
        "comment_count": 2,
        "description": "d1",
        "url": "https://www.youtube.com/watch?v=vid1",
    }
]


def _mock_ydl(page: dict) -> mock.MagicMock:
    """A YoutubeDL context-manager mock whose ``extract_info`` returns ``page``."""
    ydl = mock.MagicMock()
    ydl.extract_info.return_value = page
    cm = mock.MagicMock()
    cm.__enter__.return_value = ydl
    cm.__exit__.return_value = False
    return cm


class UrlNormalizationTests(unittest.TestCase):
    def test_appends_videos_tab(self):
        self.assertEqual(
            analyze._videos_url("https://x.tv/@a"), "https://x.tv/@a/videos"
        )

    def test_keeps_existing_videos_tab(self):
        url = "https://x.tv/@a/videos"
        self.assertEqual(analyze._videos_url(url), url)

    def test_strips_trailing_slash(self):
        self.assertEqual(
            analyze._videos_url("https://x.tv/@a/"), "https://x.tv/@a/videos"
        )


class FormattingTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(analyze._format_duration(None), "?")
        self.assertEqual(analyze._format_duration(0), "?")
        self.assertEqual(analyze._format_duration(75), "1:15")
        self.assertEqual(analyze._format_duration(3661), "1:01:01")

    def test_date(self):
        self.assertEqual(analyze._format_date("20260115"), "2026-01-15")
        self.assertEqual(analyze._format_date(None), "?")
        self.assertEqual(analyze._format_date("bad"), "?")


class ReportTests(unittest.TestCase):
    def test_report_contains_channel_and_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = analyze.write_report(CHANNEL, VIDEOS, [], output_dir=Path(tmp))
            text = path.read_text(encoding="utf-8")
        self.assertIn("# Demo Channel", text)
        self.assertIn("UC123", text)
        self.assertIn("2026-01-01", text)  # date formatted
        self.assertIn("1:01:01", text)  # duration formatted
        self.assertIn("First \\| video", text)  # pipe escaped for the table
        self.assertIn("0 / 1", text)  # transcript coverage


class StorageTests(unittest.TestCase):
    def test_save_and_read_roundtrip(self):
        transcripts = [
            {
                "video_id": "vid1",
                "language": "en",
                "is_generated": 1,
                "segment_count": 3,
                "text": "hello world",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            analyze.save(CHANNEL, VIDEOS, transcripts, db_path=db)
            conn = sqlite3.connect(db)
            try:
                channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
                title = conn.execute(
                    "SELECT title FROM videos WHERE video_id = 'vid1'"
                ).fetchone()[0]
                text = conn.execute(
                    "SELECT text FROM transcripts WHERE video_id = 'vid1'"
                ).fetchone()[0]
            finally:
                conn.close()
        self.assertEqual(channels, 1)
        self.assertEqual(title, "First | video")
        self.assertEqual(text, "hello world")


class TranscriptTests(unittest.TestCase):
    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_missing_transcript_returns_none(self, mock_api):
        mock_api.return_value.fetch.side_effect = Exception("Subtitles are disabled")
        self.assertIsNone(analyze.fetch_transcript("vid1"))

    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_transcript_success(self, mock_api):
        fetched = mock.MagicMock()
        fetched.to_raw_data.return_value = [
            {"text": "hello", "start": 0.0, "duration": 1.0},
            {"text": "world", "start": 1.0, "duration": 1.0},
        ]
        fetched.language_code = "en"
        fetched.is_generated = True
        mock_api.return_value.fetch.return_value = fetched

        result = analyze.fetch_transcript("vid1")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["segment_count"], 2)
        self.assertEqual(result["text"], "hello world")
        self.assertEqual(result["is_generated"], 1)


class IntegrationTests(unittest.TestCase):
    def test_run_success(self):
        transcript = {
            "video_id": "vid1",
            "language": "en",
            "is_generated": 1,
            "segment_count": 2,
            "text": "hi",
        }
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "c.db"
            out = Path(tmp) / "reports"
            with (
                mock.patch(
                    "creatoros.analyze.fetch_channel", return_value=(CHANNEL, VIDEOS)
                ),
                mock.patch(
                    "creatoros.analyze.fetch_transcript", return_value=transcript
                ),
            ):
                report = analyze.run(URL, db_path=db, output_dir=out)
            self.assertTrue(report.exists())
            conn = sqlite3.connect(db)
            try:
                videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
                transcripts = conn.execute(
                    "SELECT COUNT(*) FROM transcripts"
                ).fetchone()[0]
            finally:
                conn.close()
        self.assertEqual(videos, 1)
        self.assertEqual(transcripts, 1)

    def test_run_empty_channel(self):
        page = {
            "channel_id": "UC123",
            "channel": "Demo",
            "uploader_id": "@demo",
            "entries": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "c.db"
            out = Path(tmp) / "reports"
            with mock.patch(
                "creatoros.analyze.yt_dlp.YoutubeDL", return_value=_mock_ydl(page)
            ):
                report = analyze.run(URL, db_path=db, output_dir=out)
            text = report.read_text(encoding="utf-8")
            conn = sqlite3.connect(db)
            try:
                videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
                channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
            finally:
                conn.close()
        self.assertIn("Latest 0 videos", text)
        self.assertEqual(videos, 0)
        self.assertEqual(channels, 1)

    def test_invalid_url_raises_analyze_error(self):
        ydl = mock.MagicMock()
        ydl.extract_info.side_effect = DownloadError("is not a valid URL")
        cm = mock.MagicMock()
        cm.__enter__.return_value = ydl
        cm.__exit__.return_value = False
        with (
            mock.patch("creatoros.analyze.yt_dlp.YoutubeDL", return_value=cm),
            self.assertRaises(analyze.AnalyzeError),
        ):
            analyze.fetch_channel("not-a-url")

    def test_network_failure_raises_analyze_error(self):
        ydl = mock.MagicMock()
        ydl.extract_info.side_effect = DownloadError(
            "Unable to download webpage: timed out"
        )
        cm = mock.MagicMock()
        cm.__enter__.return_value = ydl
        cm.__exit__.return_value = False
        with (
            mock.patch("creatoros.analyze.yt_dlp.YoutubeDL", return_value=cm),
            self.assertRaises(analyze.AnalyzeError),
        ):
            analyze.fetch_channel(URL)


class CliTests(unittest.TestCase):
    def test_cli_handles_analyze_error(self):
        with mock.patch(
            "creatoros.cli.analyze.run", side_effect=analyze.AnalyzeError("boom")
        ):
            self.assertEqual(main(["analyze-channel", URL]), 1)

    def test_cli_success_returns_zero(self):
        with mock.patch("creatoros.cli.analyze.run", return_value=Path("x")):
            self.assertEqual(main(["analyze-channel", URL]), 0)


if __name__ == "__main__":
    unittest.main()
