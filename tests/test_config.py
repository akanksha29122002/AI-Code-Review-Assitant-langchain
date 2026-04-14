import unittest

from src.code_review_assistant.config import is_placeholder, optional_secret


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


if __name__ == "__main__":
    unittest.main()
