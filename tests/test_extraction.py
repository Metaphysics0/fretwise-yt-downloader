import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from app.downloader import DownloadResult
from app.services.extraction import extract_to_simple_path


class ExtractionConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_extractions_run_one_at_a_time(self):
        active = 0
        maximum_active = 0

        async def extract_audio(_, directory: Path):
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return DownloadResult(directory / "audio.mp3", "Title", 10, "Channel", "video")

        async def upload(_, __):
            return "https://example.com/audio.mp3"

        with (
            patch("app.services.extraction.extract_audio", extract_audio),
            patch("app.services.extraction._upload", upload),
        ):
            await asyncio.gather(
                extract_to_simple_path("https://youtu.be/first"),
                extract_to_simple_path("https://youtu.be/second"),
            )

        self.assertEqual(maximum_active, 1)


if __name__ == "__main__":
    unittest.main()
