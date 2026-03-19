from __future__ import annotations

from typing import Any

import requests

from src.code_review_assistant.github_auth import build_github_auth_provider
from src.code_review_assistant.config import settings


class GitHubClient:
    def __init__(self) -> None:
        self.base_url = settings.github_api_url.rstrip("/")
        self.auth_provider = build_github_auth_provider()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "langchain-code-review-assistant",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get_pull_request(
        self,
        owner: str,
        repo: str,
        number: int,
        installation_id: int | None = None,
    ) -> dict[str, Any]:
        return self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}", owner=owner, repo=repo, installation_id=installation_id)

    def list_pull_request_files(
        self,
        owner: str,
        repo: str,
        number: int,
        installation_id: int | None = None,
    ) -> list[dict[str, Any]]:
        page = 1
        files: list[dict[str, Any]] = []
        while True:
            batch = self._request(
                "GET",
                f"/repos/{owner}/{repo}/pulls/{number}/files",
                owner=owner,
                repo=repo,
                installation_id=installation_id,
                params={"per_page": 100, "page": page},
            )
            if not batch:
                break
            files.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return files

    def submit_review(
        self,
        owner: str,
        repo: str,
        number: int,
        commit_id: str,
        body: str,
        comments: list[dict[str, Any]],
        installation_id: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "commit_id": commit_id,
            "body": body,
            "event": "COMMENT",
        }
        if comments:
            payload["comments"] = comments
        return self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            owner=owner,
            repo=repo,
            installation_id=installation_id,
            json=payload,
        )

    def create_issue_comment(
        self,
        owner: str,
        repo: str,
        number: int,
        body: str,
        installation_id: int | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{number}/comments",
            owner=owner,
            repo=repo,
            installation_id=installation_id,
            json={"body": body},
        )

    def create_commit_status(
        self,
        owner: str,
        repo: str,
        sha: str,
        *,
        state: str,
        description: str,
        context: str,
        installation_id: int | None = None,
        target_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "state": state,
            "description": description[:140],
            "context": context,
        }
        if target_url:
            payload["target_url"] = target_url
        return self._request(
            "POST",
            f"/repos/{owner}/{repo}/statuses/{sha}",
            owner=owner,
            repo=repo,
            installation_id=installation_id,
            json=payload,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        owner: str,
        repo: str,
        installation_id: int | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        headers = self.auth_provider.get_headers(owner, repo, installation_id)
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            params=params,
            json=json,
            timeout=30,
        )
        if response.status_code >= 400:
            raise ValueError(f"GitHub API error {response.status_code}: {response.text}")
        if response.content:
            return response.json()
        return None
