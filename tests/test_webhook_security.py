import hashlib
import hmac
import unittest

from src.code_review_assistant.webhook_security import settings, verify_github_signature


class WebhookSecurityTests(unittest.TestCase):
    def test_verify_github_signature_accepts_valid_signature(self) -> None:
        original_secret = settings.github_webhook_secret
        settings.github_webhook_secret = "secret-value"
        try:
            body = b'{"action":"opened"}'
            digest = hmac.new(b"secret-value", body, hashlib.sha256).hexdigest()
            self.assertTrue(verify_github_signature(body, f"sha256={digest}"))
        finally:
            settings.github_webhook_secret = original_secret

    def test_verify_github_signature_rejects_invalid_signature(self) -> None:
        original_secret = settings.github_webhook_secret
        settings.github_webhook_secret = "secret-value"
        try:
            body = b'{"action":"opened"}'
            self.assertFalse(verify_github_signature(body, "sha256=wrong"))
        finally:
            settings.github_webhook_secret = original_secret


if __name__ == "__main__":
    unittest.main()
