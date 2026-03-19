from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PullRequestContext:
    owner: str
    repo: str
    number: int
    title: str
    body: str
    head_sha: str
    base_ref: str
    head_ref: str
    installation_id: int | None
    files: list[dict]
