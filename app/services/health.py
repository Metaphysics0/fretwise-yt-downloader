import asyncio
import importlib.metadata
import subprocess

import httpx

from app.config import COOKIE_PATH, NODE_PATH, POT_SERVER_URL, PROXY_URL, missing_environment


async def get_health() -> dict:
    missing = missing_environment()
    pot_healthy = await _pot_is_healthy()
    ready = not missing and pot_healthy

    return {
        "status": "healthy" if ready else "degraded",
        "ready": ready,
        "ytdlp_version": _package_version("yt-dlp"),
        "ejs_version": _package_version("yt-dlp-ejs"),
        "pot_provider_version": _package_version("bgutil-ytdlp-pot-provider"),
        "pot_server": "healthy" if pot_healthy else "unhealthy",
        "ffmpeg": await asyncio.to_thread(_command_version, ["ffmpeg", "-version"]),
        "node": await asyncio.to_thread(_command_version, [NODE_PATH, "--version"]),
        "cookies": _cookie_status(),
        "proxy": "configured" if PROXY_URL else "not configured",
        "missing_environment": missing,
    }


async def _pot_is_healthy() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{POT_SERVER_URL}/ping")
            return response.status_code == 200
    except Exception:
        return False


def _package_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "missing"


def _command_version(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        return (result.stdout or result.stderr).splitlines()[0].strip()
    except Exception:
        return "missing"


def _cookie_status() -> str:
    if not COOKIE_PATH.exists():
        return "missing"
    return f"found ({COOKIE_PATH.stat().st_size // 1024} KB)"
