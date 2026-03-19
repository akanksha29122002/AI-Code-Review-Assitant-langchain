# AI-Powered Code Review Assistant

This project is a fuller starter project for reviewing code changes with LangChain and an LLM. It includes:

- a Streamlit UI for manual reviews
- a FastAPI webhook service for GitHub pull request reviews
- a GitHub PR review tab inside the Streamlit UI
- GitHub API integration for fetching PR files and posting review results
- GitHub App authentication support
- SQLite-backed review history
- vector-based repository retrieval with heuristic fallback
- Gemini API support
- free local-model support through Ollama
- a built-in local fallback reviewer when the external model is unavailable
- tests for diff parsing, webhook verification, inline comment mapping, fallback review, and history persistence

## What it does

- Accepts a git diff, patch, or code snippet
- Uses a structured LangChain prompt to review the change
- Falls back to local rule-based analysis when the external LLM is unavailable
- Returns prioritized findings with severity, impact, and suggested fixes
- Shows an overall summary, risk level, and missing test recommendations
- Stores manual and GitHub-triggered reviews in SQLite
- Pulls in relevant local repository files to improve review context
- Supports a local embedding index for better repository retrieval quality
- Can preview GitHub PR reviews inside the app even when posting back to GitHub is disabled
- Publishes GitHub commit status checks based on review results when GitHub posting is enabled and permitted
- Can run with Gemini API or without OpenAI billing by using Ollama locally

## Stack

- Python
- Streamlit
- FastAPI
- LangChain
- OpenAI via `langchain-openai`
- GitHub REST API
- SQLite

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment variables:

```bash
copy .env.example .env
```

4. Choose your provider in `.env`:

- Gemini mode: `LLM_PROVIDER=gemini`
- Free local mode: `LLM_PROVIDER=ollama`
- OpenAI mode: `LLM_PROVIDER=openai`

5. Configure credentials:

- For Gemini mode, set `GEMINI_API_KEY`
- For OpenAI mode, set `OPENAI_API_KEY`
- For free local mode, install Ollama and use the default local URL

6. Configure GitHub authentication in one of these ways:

- Recommended: set `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY_PATH`, and optionally `GITHUB_INSTALLATION_ID`
- Simpler fallback: set `GITHUB_TOKEN`

7. Run the app:

```bash
streamlit run app.py
```

8. Run the webhook service in a second terminal:

```bash
uvicorn webhook_app:app --reload --port 8000
```

9. Optional but recommended: build the repository index:

```bash
python scripts/build_repository_index.py
```

## How to use

### Manual mode

1. Paste a diff or changed code into the input box.
2. Optionally add repository context, changed file summaries, or review focus areas.
3. Leave `Use local repository context` enabled if you want the app to scan nearby files.
   If a repository index exists, the app will use vector retrieval first.
4. Set `Primary language` to match the code you are reviewing.
5. Run the review.
6. Inspect findings sorted by severity and use the recommended fixes as a starting point.
7. Review history appears at the bottom of the Streamlit UI.

### GitHub PR review in the app

1. Open the `GitHub PR Review` tab in Streamlit.
2. Enter the repository owner, repository name, and pull request number.
3. Turn off `Publish review back to GitHub` if you only want a preview in the app.
4. Turn it on if your token or GitHub App has permission to post PR reviews and statuses.
5. Run the review and inspect the result in the UI.

This mode requires an existing pull request. GitHub issues and compare pages are not enough on their own.

### Free local mode with Ollama

1. Install Ollama on your machine.
2. Pull a chat model:

```bash
ollama pull llama3.1:8b
```

3. Pull an embedding model:

```bash
ollama pull nomic-embed-text
```

4. Set this in `.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

5. Start Ollama.
6. Run `python scripts/check_setup.py`
7. Run `python scripts/build_repository_index.py`
8. Run `streamlit run app.py`

### Gemini API mode

1. Set this in `.env`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=models/text-embedding-004
```

2. Run:

```bash
python scripts/check_setup.py
python scripts/build_repository_index.py
streamlit run app.py
```

### GitHub PR mode

1. Set `GITHUB_WEBHOOK_SECRET` in `.env`.
2. Configure GitHub authentication.
3. Preferred: create a GitHub App with pull request and contents read/write permissions, then set `GITHUB_APP_ID` and `GITHUB_PRIVATE_KEY_PATH`.
4. Alternative: set `GITHUB_TOKEN` with repository access.
5. Start the webhook server with `uvicorn webhook_app:app --reload --port 8000`.
6. Expose the local server with a tunnel such as `ngrok` if GitHub needs to reach your machine.
7. In your GitHub repository settings, add a webhook pointing to `/github/webhook`.
8. Subscribe the webhook to `Pull requests`.
9. Open, reopen, or update a pull request.
10. The service will fetch changed files, run the review, post the result back to the PR when permitted, and store the review in SQLite.
11. The service will also publish a GitHub commit status for the PR head SHA when GitHub posting is enabled and allowed.

## Tests

Run:

```bash
python -m unittest discover -s tests -v
```

## Local validation

Before starting the webhook server, validate your environment:

```bash
python scripts/check_setup.py
```

This checks:

- `OPENAI_API_KEY`
- `LLM_PROVIDER`
- GitHub App or token-based auth configuration
- private key file presence
- webhook secret presence

## Reset project state

To remove generated databases, local index files, caches, and temporary folders:

```bash
python scripts/reset_project.py
```

This preserves `.env` by default.

To also replace `.env` with the template from `.env.example`:

```bash
python scripts/reset_project.py --reset-env
```

## Repository index

Build the local vector index:

```bash
python scripts/build_repository_index.py
```

Default index path:

- `data/repository_index.json`

If no index exists, the app falls back to heuristic file retrieval.

## Fallback review mode

If the configured external model is unavailable because of quota, missing packages, or provider issues, the app falls back to a built-in local reviewer.

Fallback mode currently covers:

- obvious hardcoded secrets
- debug statements left in code
- broad exception handling
- likely missing statement terminators in C-like languages
- missing test reminders

Fallback mode is useful for demos and offline resilience, but it is intentionally narrower than a full model-based review.

## Demo flow

For a reliable demo:

1. Start Streamlit:

```bash
streamlit run app.py
```

2. Use the `Manual Review` tab for a pasted diff or code snippet.
3. Set `Primary language` correctly before running the review.
4. For GitHub review, use an existing pull request in the `GitHub PR Review` tab.
5. Leave `Publish review back to GitHub` off if you only want a preview in the app.

## One-command startup

### Docker

Build and run both services:

```bash
docker compose up --build
```

Services:

- Streamlit UI: `http://localhost:8501`
- Webhook API: `http://localhost:8000`

Review history is stored locally in `data/review_history.db`.

### Windows PowerShell

Run both services locally:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_local.ps1
```

## Deployment

### Render blueprint

This repository includes [`render.yaml`](render.yaml) for a two-service Render deployment:

- `ai-code-review-ui` runs the Streamlit app
- `ai-code-review-webhook` runs the FastAPI GitHub webhook service

Deploy steps:

1. Push this project to GitHub.
2. In Render, create a new Blueprint and connect the repository.
3. Render will create both services from `render.yaml`.
4. Add the required secrets to both services:
   - `LLM_PROVIDER`
   - `GEMINI_API_KEY` or `OPENAI_API_KEY`
   - `GITHUB_TOKEN` or GitHub App settings if you want PR publishing
   - `GITHUB_WEBHOOK_SECRET` for webhook verification
5. After the webhook service is live, configure GitHub to send webhook events to:

```text
https://<your-render-webhook-host>/github/webhook
```

6. Optional: open a Render shell on the UI service and build the repository index:

```bash
python scripts/build_repository_index.py
```

Render notes:

- the free Render setup uses `/tmp`, which is ephemeral
- SQLite review history and the local repository index are lost on redeploy, restart, or free-instance spin-down
- if you need durable shared data, use an external database or move to a paid service with persistent storage

### Vercel plus Streamlit Community Cloud

This project can be deployed for free with a split setup:

- deploy the FastAPI webhook service to Vercel
- deploy the Streamlit UI to Streamlit Community Cloud

Why split it:

- Vercel officially supports Python functions and FastAPI apps
- this repository's UI is a Streamlit server, which is better suited to Streamlit Community Cloud than Vercel's function model

Files added for Vercel:

- [`api/index.py`](api/index.py) exposes the FastAPI webhook app
- [`vercel.json`](vercel.json) rewrites `/health` and `/github/webhook` to the Vercel Python function
- [`.python-version`](.python-version) pins the Python version Vercel should use
- [`.vercelignore`](.vercelignore) excludes local data, secrets, tests, and presentation files from uploads
- [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) provides a template for Streamlit Community Cloud secrets

Deploy the webhook to Vercel:

1. Push this repository to GitHub.
2. Import the repo into Vercel.
3. Set these environment variables in Vercel:
   - `LLM_PROVIDER`
   - `GEMINI_API_KEY` or `OPENAI_API_KEY`
   - `GITHUB_TOKEN` or GitHub App settings
   - `GITHUB_WEBHOOK_SECRET`
   - `REVIEW_HISTORY_DB_PATH=/tmp/review_history.db`
   - `REPOSITORY_INDEX_PATH=/tmp/repository_index.json`
4. After deploy, use this webhook URL in GitHub:

```text
https://<your-vercel-project>.vercel.app/github/webhook
```

Deploy the Streamlit UI for free:

1. Sign in to Streamlit Community Cloud.
2. Create an app from this GitHub repository.
3. Use `app.py` as the entrypoint.
4. Add the same provider credentials as Streamlit secrets.

Free-tier notes:

- both Vercel `/tmp` storage and many free app hosts are ephemeral
- Vercel Hobby functions should stay within the free-plan duration limits
- SQLite history and the local repository index should be treated as temporary in free hosting
- if you need durable shared data between webhook and UI, use an external database and object storage

## Review history

- Manual reviews are stored automatically
- GitHub PR reviews are stored automatically
- Local database path: `data/review_history.db`
- Recent reviews are shown in the Streamlit UI

## GitHub App checklist

Recommended settings for a GitHub App:

1. Create a GitHub App in GitHub Developer Settings.
2. Enable:
   `Pull requests: Read and write`
   `Contents: Read-only`
   `Metadata: Read-only`
3. Generate a private key and save the `.pem` file locally.
4. Install the app on the repository you want to review.
5. Set these values in `.env`:
   `GITHUB_APP_ID`
   `GITHUB_PRIVATE_KEY_PATH`
   `GITHUB_INSTALLATION_ID` optional
   `GITHUB_WEBHOOK_SECRET`
6. Point the GitHub App webhook or repository webhook to:
   `http://your-host/github/webhook`
7. Start the service:

```bash
uvicorn webhook_app:app --reload --port 8000
```

8. Validate local config:

```bash
python scripts/check_setup.py
```

## Environment variables

- `LLM_PROVIDER`: `gemini`, `ollama`, or `openai`
- `GEMINI_API_KEY`: required only when `LLM_PROVIDER=gemini`
- `GEMINI_MODEL`: optional, defaults to `gemini-2.0-flash`
- `GEMINI_EMBEDDING_MODEL`: optional, defaults to `models/text-embedding-004`
- `OPENAI_API_KEY`: required only when `LLM_PROVIDER=openai`
- `OPENAI_MODEL`: optional, defaults to `gpt-4.1-mini`
- `OPENAI_EMBEDDING_MODEL`: optional, defaults to `text-embedding-3-small`
- `OPENAI_TEMPERATURE`: optional, defaults to `0`
- `OLLAMA_BASE_URL`: optional, defaults to `http://localhost:11434`
- `OLLAMA_MODEL`: optional, defaults to `llama3.1:8b`
- `OLLAMA_EMBEDDING_MODEL`: optional, defaults to `nomic-embed-text`
- `GITHUB_TOKEN`: fallback auth for GitHub webhook mode
- `GITHUB_WEBHOOK_SECRET`: optional but strongly recommended
- `GITHUB_API_URL`: optional, useful for GitHub Enterprise
- `GITHUB_STATUS_CONTEXT`: optional, defaults to `ai-code-review`
- `GITHUB_STATUS_FAIL_SEVERITY`: optional, defaults to `high`
- `GITHUB_APP_ID`: recommended for GitHub App mode
- `GITHUB_INSTALLATION_ID`: optional override for GitHub App mode
- `GITHUB_PRIVATE_KEY_PATH`: path to the GitHub App private key PEM file
- `REVIEW_HISTORY_DB_PATH`: optional SQLite path, defaults to `data/review_history.db`
- `REPOSITORY_INDEX_PATH`: optional local JSON index path for repository embeddings

## Suggested next steps

- Add separate agents for security, performance, and testing review
- Add richer deduplication for repeated comments on the same finding
- Add a configurable review policy UI for status thresholds and fail conditions
