from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from src.code_review_assistant.history_store import ReviewHistoryStore
from src.code_review_assistant.github_review import GitHubReviewService
from src.code_review_assistant.webhook_security import verify_github_signature


app = FastAPI(title="GitHub Code Review Webhook")
logger = logging.getLogger(__name__)
history_store = ReviewHistoryStore()


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/github/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default=""),
    x_github_delivery: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, str]:
    body = await request.body()
    if not verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature.")

    payload = await request.json()
    if x_github_event == "ping":
        return {"status": "pong"}

    if x_github_event != "pull_request":
        return {"status": f"ignored event: {x_github_event}"}

    action = payload.get("action", "")
    if action not in {"opened", "reopened", "synchronize"}:
        return {"status": f"ignored action: {action}"}

    if x_github_delivery and not history_store.mark_delivery_processed(x_github_delivery):
        return {"status": "duplicate delivery ignored"}

    repository = payload.get("repository") or {}
    pull_request = payload.get("pull_request") or {}
    installation = payload.get("installation") or {}
    owner = (repository.get("owner") or {}).get("login")
    repo = repository.get("name")
    number = pull_request.get("number")
    installation_id = installation.get("id")

    if not owner or not repo or not number:
        raise HTTPException(status_code=400, detail="Webhook payload is missing repository or PR fields.")

    background_tasks.add_task(process_pull_request_review, owner, repo, int(number), installation_id)
    return {"status": "review queued"}


def process_pull_request_review(
    owner: str,
    repo: str,
    number: int,
    installation_id: int | None,
) -> None:
    try:
        service = GitHubReviewService()
        service.review_pull_request(owner, repo, number, installation_id)
    except Exception:
        logger.exception("Failed to process PR review for %s/%s#%s", owner, repo, number)
