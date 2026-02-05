"""
FastAPI application for YouTube audio extraction.

Provides endpoints for extracting audio from YouTube videos and uploading to R2.
"""

import os
import subprocess

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, HttpUrl

from app.downloader import extract_audio
from app.storage import upload_to_r2
from app.paths import youtube_audio_path


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


class VideoMetadata(BaseModel):
    title: str
    duration: int
    channel: str
    video_id: str


class ExtractResponse(BaseModel):
    status: str
    r2_url: str
    metadata: VideoMetadata


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
        # Download audio
        result = await extract_audio(str(request.url))

        # Upload to R2
        r2_key = youtube_audio_path(request.user_id, request.transcription_id)
        r2_url = await upload_to_r2(
            file_bytes=result.file_bytes,
            key=r2_key,
            content_type="audio/mpeg",
        )

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
        raise HTTPException(status_code=500, detail=str(e))


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
