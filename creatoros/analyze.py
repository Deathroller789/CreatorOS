"""YouTube channel ingestion: fetch -> store -> report. Sprint 2 vertical slice.

Deliberately simple and procedural: one module, one path, end to end. This is a slice
of the design in docs/modules/001-youtube-intelligence.md, not the final architecture.
Refactoring is expected after the MVP.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp.utils import DownloadError

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "database" / "creatoros.db"
OUTPUT_DIR = REPO_ROOT / "output" / "reports"
# Sample size per channel. Correlations over a handful of videos are noise; the
# intelligence module needs a real sample. Override with `--limit`.
DEFAULT_VIDEO_LIMIT = 50


class AnalyzeError(Exception):
    """Raised when a channel cannot be analyzed (bad URL, network failure, etc.)."""


class _QuietLogger:
    """Swallow yt-dlp's own console logging (issue #40 family).

    Expected per-video failures — members-only, region-locked, or deleted videos — and
    the harmless "no JS runtime" warning would otherwise print a line each and flood the
    console on a normal run. Real failures are not lost: yt-dlp still raises, and the
    caller catches the exception and re-raises it with an actionable message.
    """

    def debug(self, msg: str) -> None: ...

    def info(self, msg: str) -> None: ...

    def warning(self, msg: str) -> None: ...

    def error(self, msg: str) -> None: ...


def _videos_url(channel_url: str) -> str:
    """Point any channel-URL form at its Videos tab so we get the latest uploads."""
    url = channel_url.strip().rstrip("/")
    if url.endswith("/videos"):
        return url
    return f"{url}/videos"


def fetch_channel(
    channel_url: str, limit: int = DEFAULT_VIDEO_LIMIT
) -> tuple[dict, list[dict]]:
    """Return ``(channel, videos)`` for the channel's latest ``limit`` uploads."""
    flat_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": limit,
        "logger": _QuietLogger(),
    }
    try:
        with yt_dlp.YoutubeDL(flat_opts) as ydl:
            page = ydl.extract_info(_videos_url(channel_url), download=False)
    except DownloadError as exc:
        raise AnalyzeError(f"could not fetch channel {channel_url!r}: {exc}") from exc

    channel = {
        "channel_id": page.get("channel_id") or page.get("id"),
        "handle": page.get("uploader_id"),
        "title": page.get("channel") or page.get("uploader") or page.get("title"),
        "description": page.get("description"),
        "subscriber_count": page.get("channel_follower_count"),
        "url": page.get("channel_url") or page.get("uploader_url") or channel_url,
    }

    entries = [e for e in (page.get("entries") or []) if e][:limit]
    videos: list[dict] = []
    detail_opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "logger": _QuietLogger(),
    }
    with yt_dlp.YoutubeDL(detail_opts) as ydl:
        for entry in entries:
            video_id = entry.get("id")
            if not video_id:
                continue
            try:
                info = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}", download=False
                )
            except DownloadError:
                # Expected for members-only / region-locked / deleted videos. Dropped
                # silently here; the CLI reports the requested-vs-received shortfall
                # (issue #41) so the smaller sample is never hidden.
                continue
            videos.append(
                {
                    "video_id": video_id,
                    "title": info.get("title"),
                    "upload_date": info.get("upload_date"),
                    "duration": info.get("duration"),
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "comment_count": info.get("comment_count"),
                    "description": info.get("description"),
                    "url": info.get("webpage_url")
                    or f"https://www.youtube.com/watch?v={video_id}",
                }
            )
    return channel, videos


def fetch_transcript(video_id: str) -> dict | None:
    """Fetch a video's transcript, or ``None`` if none is available.

    Captions fail in many ways (disabled, missing, IP-blocked); for the MVP we treat
    every failure the same — no transcript — and keep going.
    """
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id)
    except Exception:  # noqa: BLE001 — captions fail in many normal ways; treat all alike
        # Silent by design. A per-video print here dumps the transcript library's
        # multi-line error/help text for *every* failure, filling the console on a run
        # where captions are simply disabled (issue #40). The caller emits one grouped
        # summary line instead — ADR-009: warnings calm and grouped, retries invisible.
        return None

    snippets = fetched.to_raw_data()
    return {
        "video_id": video_id,
        "language": getattr(fetched, "language_code", None),
        "is_generated": int(bool(getattr(fetched, "is_generated", False))),
        "segment_count": len(snippets),
        "text": " ".join(s["text"] for s in snippets),
    }


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            handle TEXT,
            title TEXT,
            description TEXT,
            subscriber_count INTEGER,
            url TEXT,
            fetched_at TEXT
        );
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            channel_id TEXT,
            title TEXT,
            upload_date TEXT,
            duration INTEGER,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            description TEXT,
            url TEXT,
            fetched_at TEXT
        );
        CREATE TABLE IF NOT EXISTS transcripts (
            video_id TEXT PRIMARY KEY,
            language TEXT,
            is_generated INTEGER,
            segment_count INTEGER,
            text TEXT,
            fetched_at TEXT
        );
        """
    )
    return conn


def save(
    channel: dict,
    videos: list[dict],
    transcripts: list[dict],
    db_path: Path = DB_PATH,
) -> None:
    """Persist the channel, videos, and transcripts to SQLite (upsert)."""
    now = datetime.now(UTC).isoformat(timespec="seconds")
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO channels VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                channel["channel_id"],
                channel["handle"],
                channel["title"],
                channel["description"],
                channel["subscriber_count"],
                channel["url"],
                now,
            ),
        )
        for v in videos:
            conn.execute(
                "INSERT OR REPLACE INTO videos VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    v["video_id"],
                    channel["channel_id"],
                    v["title"],
                    v["upload_date"],
                    v["duration"],
                    v["view_count"],
                    v["like_count"],
                    v["comment_count"],
                    v["description"],
                    v["url"],
                    now,
                ),
            )
        for t in transcripts:
            conn.execute(
                "INSERT OR REPLACE INTO transcripts VALUES (?, ?, ?, ?, ?, ?)",
                (
                    t["video_id"],
                    t["language"],
                    t["is_generated"],
                    t["segment_count"],
                    t["text"],
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "?"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _format_date(yyyymmdd: str | None) -> str:
    if not yyyymmdd or len(yyyymmdd) != 8:
        return "?"
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


def write_report(
    channel: dict,
    videos: list[dict],
    transcripts: list[dict],
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Write a markdown report and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    have_transcript = {t["video_id"] for t in transcripts}
    slug = (channel.get("handle") or channel.get("channel_id") or "channel").lstrip("@")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    path = output_dir / f"{slug}_{today}.md"

    subs = channel.get("subscriber_count")
    lines = [
        f"# {channel.get('title') or 'Unknown channel'}",
        "",
        f"_Report generated {today} by CreatorOS._",
        "",
        "## Channel",
        "",
        f"- **Channel ID:** `{channel.get('channel_id')}`",
        f"- **Handle:** {channel.get('handle') or '—'}",
        f"- **Subscribers:** {subs:,}" if subs else "- **Subscribers:** —",
        f"- **URL:** {channel.get('url') or '—'}",
        "",
        f"## Latest {len(videos)} videos",
        "",
        "| Title | Uploaded | Duration | Views | Transcript |",
        "| --- | --- | --- | --- | --- |",
    ]
    for v in videos:
        views = f"{v['view_count']:,}" if v.get("view_count") else "?"
        mark = "yes" if v["video_id"] in have_transcript else "no"
        title = (v.get("title") or "").replace("|", "\\|")
        lines.append(
            f"| [{title}]({v.get('url')}) | {_format_date(v.get('upload_date'))} "
            f"| {_format_duration(v.get('duration'))} | {views} | {mark} |"
        )
    lines += [
        "",
        f"Transcripts captured: **{len(have_transcript)} / {len(videos)}**.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def ingest(
    channel_url: str, limit: int = DEFAULT_VIDEO_LIMIT, db_path: Path = DB_PATH
) -> tuple[dict, list[dict], list[dict]]:
    """Fetch a channel and its latest uploads, store them, and return the raw data.

    The ingestion primitive shared by the CLI and :func:`run`: it does the raw I/O
    (network + SQLite) and hands back ``(channel, videos, transcripts)`` for a caller to
    analyze. A video whose transcript is unavailable is still kept — metadata is enough,
    and the V1 intelligence report uses metadata only.
    """
    channel, videos = fetch_channel(channel_url, limit=limit)
    transcripts: list[dict] = []
    for v in videos:
        transcript = fetch_transcript(v["video_id"])
        if transcript:
            transcripts.append(transcript)
    save(channel, videos, transcripts, db_path=db_path)
    return channel, videos, transcripts


def run(
    channel_url: str,
    limit: int = DEFAULT_VIDEO_LIMIT,
    db_path: Path = DB_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Fetch a channel, store it, and write the ingestion catalog report."""
    print(f"Analyzing {channel_url} (limit {limit}) ...")
    channel, videos, transcripts = ingest(channel_url, limit=limit, db_path=db_path)
    print(
        f"Channel: {channel['title']} ({channel['channel_id']}) - "
        f"{len(videos)} videos fetched"
    )
    report = write_report(channel, videos, transcripts, output_dir=output_dir)
    print(f"Saved to {db_path}")
    print(f"Transcripts: {len(transcripts)}/{len(videos)}")
    print(f"Report: {report}")
    return report
