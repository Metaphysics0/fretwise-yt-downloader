"""
yt-dlp wrapper for downloading YouTube audio.

Downloads audio from YouTube videos and returns the audio bytes with metadata.
"""

import os
import uuid
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
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path,
        'noplaylist': True,
        'nocheckcertificate': True,
        'no_warnings': False,
        'quiet': False,

        # Enable remote JS challenge solver for YouTube nsig
        'remote_components': ['ejs:github'],

        # PO token config (required for datacenter IPs to avoid bot detection)
        # - player_client=web: use web client which supports PO tokens
        # - webpage_skip=player_response: skip the embedded player response from the webpage
        #   (it already has LOGIN_REQUIRED), forcing a fresh API call with the PO token
        'extractor_args': {
            'youtube': {
                'player_client': ['web'],
                'webpage_skip': ['player_response'],
            },
        },

        # Anti-detection (light sleeps — residential proxy rotation handles most detection)
        'sleep_interval': 2,
        'max_sleep_interval': 5,
        'sleep_requests': 1,

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

    # Optional: proxy (supports {session} placeholder for per-request IP rotation)
    proxy_url = os.getenv('PROXY_URL')
    if proxy_url:
        session_id = uuid.uuid4().hex[:16]
        opts['proxy'] = proxy_url.replace('{session}', session_id)

    # Use browser impersonation if curl_cffi is available
    # Skip when proxy is set — Web Unlocker handles bot detection and
    # curl_cffi's TLS fingerprinting conflicts with the CONNECT tunnel
    if not proxy_url:
        try:
            from yt_dlp.networking.impersonate import ImpersonateTarget
            import curl_cffi  # noqa: F401 - just check if available
            opts['impersonate'] = ImpersonateTarget(client='chrome')
        except (ImportError, Exception):
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
