"""
Blob storage path utilities for YouTube audio.

All blob storage paths follow the pattern:
    fretwise/users/{user_id}/transcriptions/{transcription_id}/audio/youtube.mp3
"""

PROJECT_PREFIX = "fretwise"


def youtube_audio_path(user_id: str, transcription_id: str) -> str:
    """
    Build blob path for YouTube audio files.

    Args:
        user_id: The user ID (e.g., "usr_abc123")
        transcription_id: The transcription ID (e.g., "txn_xyz789")

    Returns:
        Full blob path like: fretwise/users/usr_abc/transcriptions/txn_123/audio/youtube.mp3

    Examples:
        >>> youtube_audio_path("usr_abc123", "txn_xyz789")
        'fretwise/users/usr_abc123/transcriptions/txn_xyz789/audio/youtube.mp3'
    """
    return f"{PROJECT_PREFIX}/users/{user_id}/transcriptions/{transcription_id}/audio/youtube.mp3"
