import unittest

from app.errors import DownloaderError
from app.validation import validate_video_url


class VideoUrlValidationTests(unittest.TestCase):
    def test_accepts_supported_hosts(self):
        urls = (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.tiktok.com/@user/video/123",
            "https://www.instagram.com/reel/example/",
        )

        for url in urls:
            with self.subTest(url=url):
                validate_video_url(url)

    def test_rejects_lookalike_and_unsupported_hosts(self):
        urls = (
            "https://youtube.com.example.test/watch?v=123",
            "https://example.com/video.mp4",
            "file:///etc/passwd",
        )

        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(DownloaderError):
                    validate_video_url(url)


if __name__ == "__main__":
    unittest.main()
