import asyncio
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

from app.config import COOKIE_PATH, MAX_AUDIO_BYTES, MAX_DURATION_SECONDS, NODE_PATH, PROXY_URL
from app.errors import DownloaderError, classify_download_error
from app.validation import validate_video_url


@dataclass
class DownloadResult:
    file_path: Path
    title: str
    duration: int
    channel: str
    video_id: str


def _reject_long_video(info: dict, *, incomplete: bool = False) -> str | None:
    duration = info.get("duration")
    if duration and duration > MAX_DURATION_SECONDS:
        return f"Duration exceeds the {MAX_DURATION_SECONDS}-second limit"
    return None


def _get_ytdlp_opts(output_path: str) -> dict:
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": output_path,
        "noplaylist": True,
        "match_filter": _reject_long_video,
        "js_runtimes": {
            "node": {"path": NODE_PATH},
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb"],
            },
        },
        "sleep_interval": 2,
        "max_sleep_interval": 5,
        "sleep_requests": 1,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "retry_sleep_functions": {
            "http": lambda n: min(30, 3 * (2 ** n)),
            "fragment": lambda n: min(15, 2 * (2 ** n)),
        },
    }

    if COOKIE_PATH.exists():
        opts["cookiefile"] = str(COOKIE_PATH)

    if PROXY_URL:
        session_id = uuid.uuid4().hex[:16]
        opts["proxy"] = PROXY_URL.replace("{session}", session_id)

    if not PROXY_URL:
        try:
            from yt_dlp.networking.impersonate import ImpersonateTarget
            import curl_cffi

            opts["impersonate"] = ImpersonateTarget(client="chrome")
        except Exception:
            pass

    return opts


def _download_sync(url: str, output_dir: Path) -> DownloadResult:
    validate_video_url(url)
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    try:
        opts = _get_ytdlp_opts(output_template)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloaderError:
        raise
    except Exception as error:
        raise classify_download_error(error) from error

    mp3_files = list(output_dir.glob("*.mp3"))
    if len(mp3_files) != 1:
        raise DownloaderError("conversion_failed", "Audio conversion did not produce one MP3 file", 500)

    file_path = mp3_files[0]
    if file_path.stat().st_size > MAX_AUDIO_BYTES:
        raise DownloaderError("audio_too_large", "Converted audio exceeds the 50MB limit")

    return DownloadResult(
        file_path=file_path,
        title=info.get("title") or "Video Audio",
        duration=int(info.get("duration") or 0),
        channel=info.get("channel") or info.get("uploader") or "Unknown Artist",
        video_id=info.get("id") or file_path.stem,
    )


async def extract_audio(url: str, output_dir: Path) -> DownloadResult:
    return await asyncio.to_thread(_download_sync, url, output_dir)


def _probe_sync(url: str) -> dict:
    validate_video_url(url)
    try:
        with yt_dlp.YoutubeDL(_get_ytdlp_opts("/tmp/%(id)s.%(ext)s")) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloaderError:
        raise
    except Exception as error:
        raise classify_download_error(error) from error

    audio_formats = sum(1 for item in info.get("formats", []) if item.get("acodec") != "none")
    if audio_formats == 0:
        raise DownloaderError("no_audio_formats", "No downloadable audio formats were found", 503, True)

    return {
        "status": "healthy",
        "video_id": info.get("id") or "unknown",
        "title": info.get("title") or "Unknown title",
        "audio_formats": audio_formats,
    }


async def probe_video(url: str) -> dict:
    return await asyncio.to_thread(_probe_sync, url)
