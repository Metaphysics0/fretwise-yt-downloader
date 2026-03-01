"""
Blob storage path utilities for audio extracted from video platforms.

All blob storage paths follow the pattern:
    fretwise/users/{user_id}/transcriptions/{transcription_id}/audio/{platform}.mp3

Supported platforms: youtube, instagram, tiktok
"""

PROJECT_PREFIX = "fretwise"


def detect_platform(url: str) -> str:
    """
    Detect the platform from a URL.

    Returns a platform slug: "youtube", "instagram", or "tiktok".
    Falls back to "youtube" for unrecognised URLs (yt-dlp will raise on bad URLs anyway).
    """
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "instagram.com" in url_lower:
        return "instagram"
    if "tiktok.com" in url_lower:
        return "tiktok"
    return "youtube"


def audio_path(platform: str, user_id: str, transcription_id: str) -> str:
    """
    Build blob path for extracted audio files.

    Examples:
        >>> audio_path("youtube", "usr_abc", "txn_xyz")
        'fretwise/users/usr_abc/transcriptions/txn_xyz/audio/youtube.mp3'
        >>> audio_path("instagram", "usr_abc", "txn_xyz")
        'fretwise/users/usr_abc/transcriptions/txn_xyz/audio/instagram.mp3'
    """
    return f"{PROJECT_PREFIX}/users/{user_id}/transcriptions/{transcription_id}/audio/{platform}.mp3"


def youtube_audio_path(user_id: str, transcription_id: str) -> str:
    """Kept for backward compatibility. Use audio_path() instead."""
    return audio_path("youtube", user_id, transcription_id)
