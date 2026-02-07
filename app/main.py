"""
FastAPI application for YouTube audio extraction.

Provides endpoints for extracting audio from YouTube videos and uploading to R2.
"""

import os
import subprocess
import logging
import traceback
import httpx
import sentry_sdk

from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from pydantic import BaseModel, HttpUrl

from app.downloader import extract_audio
from app.storage import upload_to_r2
from app.paths import youtube_audio_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        send_default_pii=True,
        enable_logs=True,
    )
else:
    logger.warning("Sentry disabled: SENTRY_DSN is not set")


app = FastAPI(
    title="FretWise YouTube Audio Extractor",
    description="Downloads audio from YouTube and uploads to R2",
    version="1.0.0",
)


# Request/Response models

class ExtractRequest(BaseModel):
    url: HttpUrl
    user_id: str
    transcription_id: str


class ExtractAsyncRequest(BaseModel):
    url: HttpUrl
    user_id: str
    transcription_id: str
    webhook_url: HttpUrl


class ExtractSimpleRequest(BaseModel):
    url: HttpUrl


class VideoMetadata(BaseModel):
    title: str
    duration: int
    channel: str
    video_id: str


class ExtractResponse(BaseModel):
    status: str
    r2_url: str
    metadata: VideoMetadata


class ExtractAsyncResponse(BaseModel):
    status: str
    message: str


class WebhookPayload(BaseModel):
    status: str  # "completed" or "error"
    transcription_id: str
    r2_url: str | None = None
    error: str | None = None
    metadata: VideoMetadata | None = None


class HealthResponse(BaseModel):
    status: str
    ytdlp_version: str


# Auth dependency

async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key from request header."""
    expected_key = os.environ.get('API_KEY')
    if not expected_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# Endpoints

@app.post("/extract", response_model=ExtractResponse)
async def extract_endpoint(
    request: ExtractRequest,
    _: str = Depends(verify_api_key),
):
    """
    Extract audio from a YouTube video and upload to R2.

    This endpoint:
    1. Downloads audio from the YouTube URL using yt-dlp
    2. Uploads the MP3 to R2 at the user-scoped path
    3. Returns the public R2 URL and video metadata

    Note: This is a synchronous operation that blocks for 15-45 seconds.
    """
    try:
        logger.info(f"Processing extract request for URL: {request.url}")

        # Download audio
        logger.info("Starting audio download...")
        result = await extract_audio(str(request.url))
        logger.info(f"Download complete: {result.title} ({result.duration}s)")

        # Upload to R2
        r2_key = youtube_audio_path(request.user_id, request.transcription_id)
        logger.info(f"Uploading to R2: {r2_key}")
        r2_url = await upload_to_r2(
            file_bytes=result.file_bytes,
            key=r2_key,
            content_type="audio/mpeg",
        )
        logger.info(f"Upload complete: {r2_url}")

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

    except Exception as e:
        error_detail = str(e) or f"{type(e).__name__}: {repr(e)}"
        logger.error(f"Extract failed: {error_detail}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


async def process_extract_and_webhook(
    url: str,
    user_id: str,
    transcription_id: str,
    webhook_url: str,
):
    """Background task: download, upload to R2, then call webhook."""
    try:
        logger.info(f"[ASYNC] Starting extract for {url}")

        # Download audio
        result = await extract_audio(url)
        logger.info(f"[ASYNC] Download complete: {result.title} ({result.duration}s)")

        # Upload to R2
        r2_key = youtube_audio_path(user_id, transcription_id)
        logger.info(f"[ASYNC] Uploading to R2: {r2_key}")
        r2_url = await upload_to_r2(
            file_bytes=result.file_bytes,
            key=r2_key,
            content_type="audio/mpeg",
        )
        logger.info(f"[ASYNC] Upload complete: {r2_url}")

        # Call webhook with success
        payload = WebhookPayload(
            status="completed",
            transcription_id=transcription_id,
            r2_url=r2_url,
            metadata=VideoMetadata(
                title=result.title,
                duration=result.duration,
                channel=result.channel,
                video_id=result.video_id,
            ),
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"[ASYNC] Calling webhook: {webhook_url}")
            response = await client.post(webhook_url, json=payload.model_dump())
            logger.info(f"[ASYNC] Webhook response: {response.status_code}")

    except Exception as e:
        error_detail = str(e) or f"{type(e).__name__}: {repr(e)}"
        logger.error(f"[ASYNC] Extract failed: {error_detail}")
        logger.error(traceback.format_exc())

        # Call webhook with error
        try:
            payload = WebhookPayload(
                status="error",
                transcription_id=transcription_id,
                error=error_detail,
            )
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(webhook_url, json=payload.model_dump())
        except Exception as webhook_err:
            logger.error(f"[ASYNC] Failed to call error webhook: {webhook_err}")


@app.post("/extract-async", response_model=ExtractAsyncResponse)
async def extract_async_endpoint(
    request: ExtractAsyncRequest,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key),
):
    """
    Extract audio from a YouTube video asynchronously.

    This endpoint:
    1. Accepts the request and returns immediately
    2. Downloads audio in the background
    3. Uploads to R2
    4. Calls the webhook_url with the result

    Webhook payload on success:
    {
        "status": "completed",
        "transcription_id": "...",
        "r2_url": "https://...",
        "metadata": { "title": "...", "duration": 123, "channel": "...", "video_id": "..." }
    }

    Webhook payload on error:
    {
        "status": "error",
        "transcription_id": "...",
        "error": "Error message"
    }
    """
    logger.info(f"[ASYNC] Queued extract request for URL: {request.url}")

    background_tasks.add_task(
        process_extract_and_webhook,
        str(request.url),
        request.user_id,
        request.transcription_id,
        str(request.webhook_url),
    )

    return ExtractAsyncResponse(
        status="accepted",
        message="Download queued. Webhook will be called on completion.",
    )


@app.post("/extract-simple", response_model=ExtractResponse)
async def extract_simple_endpoint(
    request: ExtractSimpleRequest,
    _: str = Depends(verify_api_key),
):
    """
    Extract audio from a YouTube video with a simple storage path.

    This is a simplified endpoint for general use that stores files at:
        downloads/{video_id}.mp3

    Useful for testing or non-FretWise applications.
    """
    try:
        logger.info(f"Processing simple extract request for URL: {request.url}")

        # Download audio
        logger.info("Starting audio download...")
        result = await extract_audio(str(request.url))
        logger.info(f"Download complete: {result.title} ({result.duration}s)")

        # Upload to R2 with simple path
        r2_key = f"downloads/{result.video_id}.mp3"
        logger.info(f"Uploading to R2: {r2_key}")
        r2_url = await upload_to_r2(
            file_bytes=result.file_bytes,
            key=r2_key,
            content_type="audio/mpeg",
        )
        logger.info(f"Upload complete: {r2_url}")

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

    except Exception as e:
        error_detail = str(e) or f"{type(e).__name__}: {repr(e)}"
        logger.error(f"Simple extract failed: {error_detail}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/health", response_model=HealthResponse)
async def health_endpoint():
    """
    Health check endpoint.

    Returns service status and yt-dlp version.
    """
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        ytdlp_version = result.stdout.strip()
    except Exception:
        ytdlp_version = "unknown"

    return HealthResponse(
        status="healthy",
        ytdlp_version=ytdlp_version,
    )
