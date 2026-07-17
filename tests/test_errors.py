import unittest

from app.errors import classify_download_error


class DownloadErrorClassificationTests(unittest.TestCase):
    def test_classifies_duration_limit(self):
        error = classify_download_error(Exception("Duration exceeds the 1800-second limit"))

        self.assertEqual(error.code, "duration_exceeded")
        self.assertFalse(error.retryable)

    def test_classifies_youtube_block(self):
        error = classify_download_error(Exception("Sign in to confirm you're not a bot"))

        self.assertEqual(error.code, "blocked")
        self.assertTrue(error.retryable)

    def test_classifies_rate_limit(self):
        error = classify_download_error(Exception("HTTP Error 429: Too Many Requests"))

        self.assertEqual(error.code, "rate_limited")
        self.assertEqual(error.status_code, 429)
        self.assertTrue(error.retryable)


if __name__ == "__main__":
    unittest.main()
