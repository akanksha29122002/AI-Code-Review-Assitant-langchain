from __future__ import annotations

import hashlib
import hmac

from src.code_review_assistant.config import settings


def verify_github_signature(body: bytes, signature_header: str | None) -> bool:
    secret = settings.github_webhook_secret
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    received = signature_header.split("=", maxsplit=1)[1]
    return hmac.compare_digest(expected, received)
