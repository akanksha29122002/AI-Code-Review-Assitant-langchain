import unittest

from src.code_review_assistant.config import default_runtime_path, is_placeholder, optional_secret


class ConfigTests(unittest.TestCase):
    def test_is_placeholder_detects_template_values(self) -> None:
        self.assertTrue(is_placeholder(None))
        self.assertTrue(is_placeholder(""))
        self.assertTrue(is_placeholder("your_gemini_api_key"))
        self.assertTrue(is_placeholder("replace_with_token"))
        self.assertTrue(is_placeholder("changeme"))
        self.assertFalse(is_placeholder("ghp_realisticTokenValue"))

    def test_optional_secret_treats_placeholders_as_unset(self) -> None:
        import os

        original = os.environ.get("TEST_SECRET_PLACEHOLDER")
        os.environ["TEST_SECRET_PLACEHOLDER"] = "your_token"
        try:
            self.assertIsNone(optional_secret("TEST_SECRET_PLACEHOLDER"))
            os.environ["TEST_SECRET_PLACEHOLDER"] = "real-token"
            self.assertEqual(optional_secret("TEST_SECRET_PLACEHOLDER"), "real-token")
        finally:
            if original is None:
                os.environ.pop("TEST_SECRET_PLACEHOLDER", None)
            else:
                os.environ["TEST_SECRET_PLACEHOLDER"] = original

    def test_default_runtime_path_uses_tmp_on_vercel(self) -> None:
        import os

        original = os.environ.get("VERCEL")
        try:
            os.environ.pop("VERCEL", None)
            self.assertEqual(default_runtime_path("review_history.db"), "data/review_history.db")
            os.environ["VERCEL"] = "1"
            self.assertEqual(default_runtime_path("review_history.db"), "/tmp/review_history.db")
        finally:
            if original is None:
                os.environ.pop("VERCEL", None)
            else:
                os.environ["VERCEL"] = original


if __name__ == "__main__":
    unittest.main()
