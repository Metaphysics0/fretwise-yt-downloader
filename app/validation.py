from urllib.parse import urlparse

from app.errors import DownloaderError


SUPPORTED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "tiktok.com",
    "www.tiktok.com",
    "vm.tiktok.com",
    "instagram.com",
    "www.instagram.com",
}


def validate_video_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in SUPPORTED_HOSTS:
        raise DownloaderError("invalid_url", "Unsupported or invalid video URL", 400)
