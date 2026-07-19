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
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    YouTubeTranscriptApiException,
)
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


class _Disabled(TranscriptsDisabled):
    """A permanent 'this video has no captions' error, constructed without arguments."""

    def __init__(self) -> None:  # noqa: D107 — a test double, not a real error
        pass


class _Transient(YouTubeTranscriptApiException):
    """A transient library failure (rate limit, upstream hiccup)."""

    def __init__(self) -> None:  # noqa: D107 — a test double, not a real error
        pass


def _track(text: str, *, generated: bool, language: str = "en") -> mock.MagicMock:
    """A caption track whose ``fetch()`` yields one snippet per word."""
    fetched = mock.MagicMock()
    fetched.to_raw_data.return_value = [
        {"text": word, "start": float(i), "duration": 1.0}
        for i, word in enumerate(text.split())
    ]
    fetched.language_code = language
    fetched.is_generated = generated
    track = mock.MagicMock()
    track.is_generated = generated
    track.fetch.return_value = fetched
    return track


class TranscriptTests(unittest.TestCase):
    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_transcript_success(self, mock_api):
        listing = mock.MagicMock()
        listing.find_manually_created_transcript.return_value = _track(
            "hello world", generated=False
        )
        mock_api.return_value.list.return_value = listing

        result = analyze.fetch_transcript("vid1")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["segment_count"], 2)
        self.assertEqual(result["text"], "hello world")
        self.assertEqual(result["is_generated"], 0)

    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_prefers_a_human_written_track_over_a_generated_one(self, mock_api):
        # A human caption track has real punctuation and no recognition noise, so it is
        # materially better evidence — it must win whenever it exists.
        listing = mock.MagicMock()
        listing.find_manually_created_transcript.return_value = _track(
            "written by a person", generated=False
        )
        listing.find_generated_transcript.return_value = _track(
            "made by a machine", generated=True
        )
        mock_api.return_value.list.return_value = listing

        result = analyze.fetch_transcript("vid1")
        self.assertEqual(result["text"], "written by a person")
        self.assertEqual(result["is_generated"], 0)

    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_falls_back_to_a_generated_track(self, mock_api):
        listing = mock.MagicMock()
        listing.find_manually_created_transcript.side_effect = _Transient()
        listing.find_generated_transcript.return_value = _track(
            "made by a machine", generated=True
        )
        mock_api.return_value.list.return_value = listing

        result = analyze.fetch_transcript("vid1")
        self.assertEqual(result["text"], "made by a machine")
        self.assertEqual(result["is_generated"], 1)

    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_captions_disabled_is_permanent_and_not_retried(self, mock_api):
        mock_api.return_value.list.side_effect = _Disabled()
        record, status = analyze.fetch_transcript_with_status(
            "vid1", sleep=lambda _: None
        )
        self.assertIsNone(record)
        self.assertEqual(status, "unavailable")
        # Permanent means permanent: asking again would not change the answer.
        self.assertEqual(mock_api.return_value.list.call_count, 1)

    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_transient_failure_is_retried_then_reported_as_blocked(self, mock_api):
        # A rate limit is not "this video has no captions". Reporting it that way
        # destroys transcript coverage for whole channels, so it is retried and, if it
        # still fails, reported as blocked rather than unavailable.
        mock_api.return_value.list.side_effect = _Transient()
        slept: list[float] = []
        record, status = analyze.fetch_transcript_with_status(
            "vid1", sleep=slept.append
        )
        self.assertIsNone(record)
        self.assertEqual(status, "blocked")
        self.assertEqual(mock_api.return_value.list.call_count, 3)
        self.assertEqual(slept, [2.0, 5.0])

    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_a_transient_failure_that_recovers_returns_the_transcript(self, mock_api):
        listing = mock.MagicMock()
        listing.find_manually_created_transcript.return_value = _track(
            "second time lucky", generated=False
        )
        mock_api.return_value.list.side_effect = [_Transient(), listing]

        record, status = analyze.fetch_transcript_with_status(
            "vid1", sleep=lambda _: None
        )
        self.assertEqual(status, "ok")
        self.assertEqual(record["text"], "second time lucky")

    @mock.patch("creatoros.analyze.YouTubeTranscriptApi")
    def test_an_empty_caption_track_is_not_a_transcript(self, mock_api):
        # A track that exists but carries no words would claim coverage the data does
        # not have (ADR-009: never overstate).
        listing = mock.MagicMock()
        listing.find_manually_created_transcript.return_value = _track(
            "", generated=False
        )
        mock_api.return_value.list.return_value = listing
        self.assertIsNone(analyze.fetch_transcript("vid1"))


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
                    "creatoros.analyze.fetch_transcript_with_status",
                    return_value=(transcript, "ok"),
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


class VideoLimitTests(unittest.TestCase):
    def test_fetch_channel_respects_limit(self):
        page = {
            "channel_id": "UC123",
            "channel": "Demo",
            "uploader_id": "@demo",
            "entries": [{"id": f"vid{i}"} for i in range(5)],
        }
        with mock.patch(
            "creatoros.analyze.yt_dlp.YoutubeDL", return_value=_mock_ydl(page)
        ) as mock_ydl_cls:
            _, videos = analyze.fetch_channel(URL, limit=2)

        # only `limit` videos are fetched...
        self.assertEqual(len(videos), 2)
        # ...and the limit is pushed down to yt-dlp rather than filtered after the fact
        flat_opts = mock_ydl_cls.call_args_list[0][0][0]
        self.assertEqual(flat_opts["playlistend"], 2)


class IngestTests(unittest.TestCase):
    def test_ingest_stores_and_returns_raw_data(self):
        transcript = {
            "video_id": "vid1",
            "language": "en",
            "is_generated": 1,
            "segment_count": 1,
            "text": "hi",
        }
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "c.db"
            with (
                mock.patch(
                    "creatoros.analyze.fetch_channel", return_value=(CHANNEL, VIDEOS)
                ),
                mock.patch(
                    "creatoros.analyze.fetch_transcript_with_status",
                    return_value=(transcript, "ok"),
                ),
            ):
                channel, videos, transcripts = analyze.ingest(URL, db_path=db)
            conn = sqlite3.connect(db)
            try:
                stored = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
            finally:
                conn.close()
        self.assertEqual(channel["channel_id"], "UC123")
        self.assertEqual(len(videos), 1)
        self.assertEqual(len(transcripts), 1)
        self.assertEqual(stored, 1)

    def test_ingest_keeps_videos_without_transcripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "c.db"
            with (
                mock.patch(
                    "creatoros.analyze.fetch_channel", return_value=(CHANNEL, VIDEOS)
                ),
                mock.patch(
                    "creatoros.analyze.fetch_transcript_with_status",
                    return_value=(None, "unavailable"),
                ),
            ):
                _, videos, transcripts = analyze.ingest(URL, db_path=db)
        self.assertEqual(len(videos), 1)
        self.assertEqual(transcripts, [])


if __name__ == "__main__":
    unittest.main()
