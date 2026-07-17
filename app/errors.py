from dataclasses import dataclass


@dataclass
class DownloaderError(Exception):
    code: str
    message: str
    status_code: int = 422
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


def classify_download_error(error: Exception) -> DownloaderError:
    message = str(error).strip() or type(error).__name__
    normalized = message.lower()

    if "duration exceeds" in normalized:
        return DownloaderError("duration_exceeded", message)
    if "unsupported url" in normalized or "is not a valid url" in normalized:
        return DownloaderError("invalid_url", "Unsupported or invalid video URL", 400)
    if any(term in normalized for term in ("private video", "members-only", "login required")):
        return DownloaderError("authentication_required", message)
    if any(term in normalized for term in ("video unavailable", "not available", "has been removed")):
        return DownloaderError("video_unavailable", message)
    if "429" in normalized or "too many requests" in normalized:
        return DownloaderError("rate_limited", message, 429, True)
    if any(term in normalized for term in ("confirm you're not a bot", "confirm you’re not a bot", "http error 403")):
        return DownloaderError("blocked", message, 503, True)
    if any(term in normalized for term in ("timed out", "timeout", "temporary failure", "connection reset")):
        return DownloaderError("download_timeout", message, 504, True)
    if "ffmpeg" in normalized:
        return DownloaderError("conversion_failed", message, 500)

    return DownloaderError("download_failed", message, 500)
