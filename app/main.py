import logging
import os

import sentry_sdk
from fastapi import BackgroundTasks, Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse

from app.errors import DownloaderError
from app.models import (
    ErrorDetail,
    ErrorResponse,
    ExtractAsyncRequest,
    ExtractAsyncResponse,
    ExtractRequest,
    ExtractResponse,
    ExtractSimpleRequest,
    ProbeRequest,
    ProbeResponse,
)
from app.downloader import probe_video
from app.services.extraction import extract_and_notify, extract_to_simple_path, extract_to_user_path
from app.services.health import get_health


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(dsn=sentry_dsn)

app = FastAPI(title="FretWise Audio Extractor", version="2.0.0")


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    expected = os.getenv("API_KEY")
    if not expected:
        raise DownloaderError("service_unavailable", "Downloader is not configured", 503, True)
    if x_api_key != expected:
        raise DownloaderError("unauthorized", "Invalid API key", 401)
    return x_api_key


@app.exception_handler(DownloaderError)
async def handle_downloader_error(_: Request, error: DownloaderError) -> JSONResponse:
    logger.error("Extraction failed", extra={"code": error.code, "retryable": error.retryable})
    body = ErrorResponse(
        error=ErrorDetail(code=error.code, message=error.message, retryable=error.retryable)
    )
    return JSONResponse(status_code=error.status_code, content=body.model_dump())


@app.post("/extract", response_model=ExtractResponse)
async def extract_endpoint(request: ExtractRequest, _: str = Depends(verify_api_key)):
    return await extract_to_user_path(str(request.url), request.user_id, request.transcription_id)


@app.post("/extract-simple", response_model=ExtractResponse)
async def extract_simple_endpoint(request: ExtractSimpleRequest, _: str = Depends(verify_api_key)):
    return await extract_to_simple_path(str(request.url))


@app.post("/extract-async", response_model=ExtractAsyncResponse)
async def extract_async_endpoint(
    request: ExtractAsyncRequest,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key),
):
    background_tasks.add_task(
        extract_and_notify,
        str(request.url),
        request.user_id,
        request.transcription_id,
        str(request.webhook_url),
    )
    return ExtractAsyncResponse(status="accepted", message="Download queued")


@app.post("/probe", response_model=ProbeResponse)
async def probe_endpoint(request: ProbeRequest, _: str = Depends(verify_api_key)):
    return await probe_video(str(request.url))


@app.get("/health")
async def health_endpoint():
    return await get_health()


@app.get("/ready")
async def readiness_endpoint():
    health = await get_health()
    return JSONResponse(status_code=200 if health["ready"] else 503, content=health)
