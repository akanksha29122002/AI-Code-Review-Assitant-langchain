from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.code_review_assistant.history_store import ReviewHistoryStore
from src.code_review_assistant.github_review import GitHubReviewService
from src.code_review_assistant.reviewer import CodeReviewAssistant
from src.code_review_assistant.webhook_security import verify_github_signature


app = FastAPI(title="AI Code Review Assistant")
logger = logging.getLogger(__name__)
history_store = ReviewHistoryStore()


DEMO_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Code Review Assistant</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17211f;
      --muted: #53615d;
      --line: #dbe5e1;
      --paper: #f7faf9;
      --panel: #ffffff;
      --teal: #0f8f83;
      --coral: #d94d43;
      font-family: "Segoe UI", Arial, sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--paper); color: var(--ink); line-height: 1.5; }
    main { max-width: 1120px; margin: 0 auto; padding: 42px 20px 56px; }
    h1 { margin: 0 0 10px; font-size: clamp(32px, 6vw, 58px); line-height: 1.05; }
    p { color: var(--muted); font-size: 18px; max-width: 820px; }
    .layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 0.8fr); gap: 20px; margin-top: 28px; }
    section { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 18px; }
    label { display: block; font-weight: 700; margin-bottom: 8px; }
    textarea, input, select {
      width: 100%; border: 1px solid var(--line); border-radius: 8px; padding: 12px;
      font: 15px/1.45 Consolas, "Courier New", monospace; color: var(--ink); background: #fbfdfc;
    }
    textarea { min-height: 330px; resize: vertical; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 12px 0; }
    button { border: 0; background: var(--teal); color: white; border-radius: 8px; padding: 12px 16px; font-weight: 800; cursor: pointer; }
    button:disabled { opacity: 0.7; cursor: wait; }
    pre { white-space: pre-wrap; word-break: break-word; background: #10201d; color: #edf8f4; border-radius: 8px; padding: 16px; min-height: 330px; margin: 0; }
    .badge { display: inline-block; color: white; background: var(--coral); border-radius: 8px; padding: 4px 8px; font-size: 13px; font-weight: 800; }
    .hint { font-size: 14px; color: var(--muted); margin-top: 10px; }
    @media (max-width: 860px) { .layout, .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <span class="badge">Live Demo</span>
    <h1>AI Code Review Assistant</h1>
    <p>Paste a diff or code snippet and get a structured review with risk, findings, suggestions, and missing-test ideas. The deployed demo falls back to local rule-based review when cloud model keys are not configured.</p>
    <div class="layout">
      <section>
        <label for="diff">Diff or code</label>
        <textarea id="diff">diff --git a/src/payments.py b/src/payments.py
@@ -0,0 +1,10 @@
+API_KEY = "sk_live_demo_key"
+
+def charge_customer(customer_id, amount):
+    print("charging customer", customer_id)
+    try:
+        if amount <= 0:
+            return {"ok": False}
+        return {"ok": True}
+    except Exception:
+        return {"ok": False}</textarea>
        <div class="row">
          <div>
            <label for="language">Language</label>
            <input id="language" value="Python">
          </div>
          <div>
            <label for="focus">Focus areas</label>
            <input id="focus" value="Correctness, Security, Testing">
          </div>
        </div>
        <button id="review">Run Review</button>
        <div class="hint">Full Streamlit UI remains available locally with <code>streamlit run app.py</code>.</div>
      </section>
      <section>
        <label>Review result</label>
        <pre id="result">Click "Run Review" to start.</pre>
      </section>
    </div>
  </main>
  <script>
    const button = document.getElementById("review");
    const result = document.getElementById("result");
    button.addEventListener("click", async () => {
      button.disabled = true;
      result.textContent = "Reviewing...";
      try {
        const response = await fetch("/review", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            diff_text: document.getElementById("diff").value,
            language: document.getElementById("language").value,
            focus_areas: document.getElementById("focus").value.split(",").map((item) => item.trim()).filter(Boolean),
            include_suggestions: true
          })
        });
        const payload = await response.json();
        result.textContent = JSON.stringify(payload, null, 2);
      } catch (error) {
        result.textContent = String(error);
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    return DEMO_HTML


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/review")
async def review_code(request: Request) -> dict:
    payload = await request.json()
    diff_text = str(payload.get("diff_text") or "")
    if not diff_text.strip():
        raise HTTPException(status_code=400, detail="diff_text is required.")

    focus_areas = payload.get("focus_areas") or ["Correctness", "Security", "Testing"]
    if not isinstance(focus_areas, list):
        focus_areas = ["Correctness", "Security", "Testing"]

    assistant = CodeReviewAssistant()
    result = assistant.review(
        repo_context=str(payload.get("repo_context") or "Public Vercel demo review."),
        retrieved_context="No additional repository files retrieved in deployed demo mode.",
        changed_files=str(payload.get("changed_files") or "No changed file summary provided."),
        diff_text=diff_text,
        language=str(payload.get("language") or "Unknown"),
        focus_areas=[str(item) for item in focus_areas],
        include_suggestions=bool(payload.get("include_suggestions", True)),
    )
    return result.model_dump()


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
