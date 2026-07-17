import logging
import tempfile
from pathlib import Path

import httpx

from app.downloader import DownloadResult, extract_audio
from app.errors import DownloaderError
from app.models import ExtractResponse, VideoMetadata
from app.paths import audio_path, detect_platform
from app.storage import upload_to_r2


logger = logging.getLogger(__name__)


def _response(result: DownloadResult, r2_url: str) -> ExtractResponse:
    return ExtractResponse(
        status="completed",
        r2_url=r2_url,
        metadata=VideoMetadata(
            title=result.title,
            duration=result.duration,
            channel=result.channel,
            video_id=result.video_id,
        ),
    )


async def extract_to_user_path(
    url: str,
    user_id: str,
    transcription_id: str,
) -> ExtractResponse:
    key = audio_path(detect_platform(url), user_id, transcription_id)
    return await _extract_and_upload(url, key)


async def extract_to_simple_path(url: str) -> ExtractResponse:
    with tempfile.TemporaryDirectory() as directory:
        result = await extract_audio(url, Path(directory))
        r2_url = await _upload(result, f"downloads/{result.video_id}.mp3")
        return _response(result, r2_url)


async def _extract_and_upload(url: str, key: str) -> ExtractResponse:
    with tempfile.TemporaryDirectory() as directory:
        result = await extract_audio(url, Path(directory))
        r2_url = await _upload(result, key)
        return _response(result, r2_url)


async def _upload(result: DownloadResult, key: str) -> str:
    try:
        return await upload_to_r2(result.file_path, key, "audio/mpeg")
    except Exception as error:
        logger.exception("R2 upload failed", extra={"key": key})
        raise DownloaderError("storage_failed", "Failed to store extracted audio", 503, True) from error


async def extract_and_notify(
    url: str,
    user_id: str,
    transcription_id: str,
    webhook_url: str,
) -> None:
    try:
        result = await extract_to_user_path(url, user_id, transcription_id)
        payload = {
            "status": "completed",
            "transcription_id": transcription_id,
            "r2_url": result.r2_url,
            "metadata": result.metadata.model_dump(),
        }
    except DownloaderError as error:
        payload = {
            "status": "error",
            "transcription_id": transcription_id,
            "error": {
                "code": error.code,
                "message": error.message,
                "retryable": error.retryable,
            },
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
    except Exception:
        logger.exception("Extraction webhook failed", extra={"transcription_id": transcription_id})
