from pydantic import BaseModel, HttpUrl


class ExtractRequest(BaseModel):
    url: HttpUrl
    user_id: str
    transcription_id: str


class ExtractAsyncRequest(ExtractRequest):
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


class ProbeRequest(BaseModel):
    url: HttpUrl


class ProbeResponse(BaseModel):
    status: str
    video_id: str
    title: str
    audio_formats: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    status: str = "error"
    error: ErrorDetail
