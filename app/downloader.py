"""
yt-dlp wrapper for downloading YouTube audio.

Downloads audio from YouTube videos and returns the audio bytes with metadata.
"""

import os
import tempfile
import asyncio
from pathlib import Path
from dataclasses import dataclass

import yt_dlp


@dataclass
class DownloadResult:
    """Result of a YouTube audio download."""
    file_bytes: bytes
    title: str
    duration: int
    channel: str
    video_id: str


def _get_ytdlp_opts(output_path: str) -> dict:
    """Get yt-dlp options configured for audio extraction."""
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'outtmpl': output_path,
        'noplaylist': True,
        'no_warnings': False,
        'quiet': False,

        # Anti-detection
        'sleep_interval': 10,
        'max_sleep_interval': 30,
        'sleep_requests': 2,

        # Resilience
        'retries': 10,
        'fragment_retries': 10,
        'retry_sleep_functions': {
            'http': lambda n: 5 * (2 ** n),
            'fragment': lambda n: 2 * (2 ** n),
        },
    }

    # Optional: cookies file
    cookie_path = os.getenv('COOKIE_PATH', '/config/cookies.txt')
    if Path(cookie_path).exists():
        opts['cookiefile'] = cookie_path

    # Optional: proxy
    proxy_url = os.getenv('PROXY_URL')
    if proxy_url:
        opts['proxy'] = proxy_url

    # Use curl_cffi for browser impersonation if available
    try:
        import curl_cffi
        opts['impersonate'] = 'chrome'
    except ImportError:
        pass

    return opts


def _download_sync(url: str) -> DownloadResult:
    """Synchronous download function to run in thread pool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, '%(id)s.%(ext)s')
        opts = _get_ytdlp_opts(output_template)

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

            video_id = info.get('id')
            mp3_path = os.path.join(tmpdir, f'{video_id}.mp3')

            with open(mp3_path, 'rb') as f:
                file_bytes = f.read()

            return DownloadResult(
                file_bytes=file_bytes,
                title=info.get('title', ''),
                duration=info.get('duration', 0),
                channel=info.get('channel', ''),
                video_id=video_id,
            )


async def extract_audio(url: str) -> DownloadResult:
    """
    Download audio from a YouTube URL.

    Args:
        url: YouTube video URL

    Returns:
        DownloadResult with file bytes and metadata

    Raises:
        yt_dlp.DownloadError: If download fails
    """
    return await asyncio.to_thread(_download_sync, url)
