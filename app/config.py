import os
import shutil
from pathlib import Path


REQUIRED_ENVIRONMENT = (
    "API_KEY",
    "R2_ENDPOINT",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "R2_PUBLIC_URL",
)

MAX_DURATION_SECONDS = int(os.getenv("MAX_DURATION_SECONDS", "1800"))
MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_BYTES", str(50 * 1024 * 1024)))
COOKIE_PATH = Path(os.getenv("COOKIE_PATH", "/config/cookies.txt"))
PROXY_URL = os.getenv("PROXY_URL")
POT_SERVER_URL = os.getenv("POT_SERVER_URL", "http://127.0.0.1:4416")
NODE_PATH = os.getenv("NODE_PATH") or shutil.which("node") or "/usr/local/bin/node"


def missing_environment() -> list[str]:
    return [name for name in REQUIRED_ENVIRONMENT if not os.getenv(name)]
