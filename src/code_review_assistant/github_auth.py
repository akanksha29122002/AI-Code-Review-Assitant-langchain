from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import jwt
import requests

from src.code_review_assistant.config import settings


class GitHubAuthProvider:
    def get_headers(self, owner: str, repo: str, installation_id: int | None = None) -> dict[str, str]:
        raise NotImplementedError


class NoAuthProvider(GitHubAuthProvider):
    def get_headers(self, owner: str, repo: str, installation_id: int | None = None) -> dict[str, str]:
        return {}


class TokenAuthProvider(GitHubAuthProvider):
    def __init__(self, token: str) -> None:
        self.token = token

    def get_headers(self, owner: str, repo: str, installation_id: int | None = None) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class GitHubAppAuthProvider(GitHubAuthProvider):
    def __init__(self, app_id: str, private_key: str, base_url: str) -> None:
        self.app_id = app_id
        self.private_key = private_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self._cached_token: str | None = None
        self._cached_token_expiry: float = 0
        self._cached_installation_id: int | None = None

    def get_headers(self, owner: str, repo: str, installation_id: int | None = None) -> dict[str, str]:
        token = self._get_installation_token(owner, repo, installation_id)
        return {"Authorization": f"Bearer {token}"}

    def _get_installation_token(self, owner: str, repo: str, installation_id: int | None) -> str:
        now = time.time()
        if (
            self._cached_token
            and self._cached_installation_id == installation_id
            and now < self._cached_token_expiry - 60
        ):
            return self._cached_token

        resolved_installation_id = installation_id or self._resolve_installation_id(owner, repo)
        response = self.session.post(
            f"{self.base_url}/app/installations/{resolved_installation_id}/access_tokens",
            headers=self._build_app_headers(),
            timeout=30,
        )
        if response.status_code >= 400:
            raise ValueError(
                f"GitHub App token request failed with {response.status_code}: {response.text}"
            )

        payload = response.json()
        self._cached_token = payload["token"]
        expires_at = payload.get("expires_at", "")
        self._cached_token_expiry = _parse_github_expiry(expires_at)
        self._cached_installation_id = resolved_installation_id
        return self._cached_token

    def _resolve_installation_id(self, owner: str, repo: str) -> int:
        if settings.github_installation_id:
            return int(settings.github_installation_id)
        response = self.session.get(
            f"{self.base_url}/repos/{owner}/{repo}/installation",
            headers=self._build_app_headers(),
            timeout=30,
        )
        if response.status_code >= 400:
            raise ValueError(
                f"GitHub App installation lookup failed with {response.status_code}: {response.text}"
            )
        payload = response.json()
        return int(payload["id"])

    def _build_app_headers(self) -> dict[str, str]:
        jwt_token = self._build_jwt()
        return {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "langchain-code-review-assistant",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _build_jwt(self) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "iat": now - 60,
            "exp": now + 540,
            "iss": self.app_id,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")


def build_github_auth_provider() -> GitHubAuthProvider:
    if settings.uses_github_app:
        private_key = settings.github_private_key
        if not private_key:
            raise ValueError("GitHub App auth is enabled but the private key could not be loaded.")
        return GitHubAppAuthProvider(
            app_id=settings.github_app_id or "",
            private_key=private_key,
            base_url=settings.github_api_url,
        )
    if settings.github_token:
        return TokenAuthProvider(settings.github_token)
    return NoAuthProvider()


def _parse_github_expiry(expires_at: str) -> float:
    if not expires_at:
        return time.time() + 300
    normalized = expires_at.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).timestamp()
